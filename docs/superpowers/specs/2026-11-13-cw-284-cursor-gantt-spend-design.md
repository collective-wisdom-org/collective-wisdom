# CW-284: Show tokens and spend on the gantt rows of Cursor threads

**Status:** Shipped
**Shipped:** in PR #287, as specified
**Ticket:** [#284](https://github.com/collective-wisdom-org/collective-wisdom/issues/284)
**Related:** [#258](https://github.com/collective-wisdom-org/collective-wisdom/issues/258) (Cursor gantt snapshots), [#257](https://github.com/collective-wisdom-org/collective-wisdom/issues/257) (Cursor usage report), [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275), [#282](https://github.com/collective-wisdom-org/collective-wisdom/issues/282)

## Goal

A Cursor thread's gantt rows on the dashboard show tokens and cost, and its snapshot has a `total`, so the ticket's spend includes the Cursor thread. The numbers come from Cursor's run store, read by the code `agent_usage.py` already has and priced from `prices.json`.

## Today

Facts from `main` at `e6219eb`.

- `agent-team/scripts/cursor_gantt_hook.ts` (CW-258) runs on six Cursor events, keeps a `CursorState` in `<root>/.agent-team/gantt/cursor/<id>.json` and writes `<root>/.agent-team/gantt/<id>.json` with `cursorSnapshot` from `mods/agent-gantt/hooks/cursor.ts`. `cursorSnapshot` calls `buildRows(records, [], null, 'Cursor')`: no price table and no usage, so every row has `tokens: 0`, `cost: null`, and the snapshot `total: null`.
- `agent-team/scripts/agent_usage.py` `read_cursor` opens each `~/.cursor/projects/*/sdk-agent-store/*/index.db` read-only and reads `runs(agent_id, turn_number, model, usage_json, coalesce(started_at, created_at))` for runs with `usage_json`. `cursor_costs` splits a run's usage into billed kinds (input is `inputTokens` minus cache read and cache write; cache writes are priced at the 5 minute rate) and prices it from `prices.json` by model family. A model with no family has no price.
- The store's `agent_id` is the hook's `conversation_id`: the trial repo's snapshot `agent-a942f8f4-….json` matches the agent `agent-a942f8f4-…` in that repo's store.
- A run is one turn (one prompt). Its `usage_json` is empty while it runs. On the trial repo the run began 3 seconds before the hook saw the prompt.
- Cursor subagents have no `runs` rows of their own (CW-257 spec). Their work is either inside the parent turn's usage or not recorded.
- `rows.ts` `buildRows(records, agents, prices, harness)` prices each row from its records' `usage` (`Record<model, Tokens>`) with `modelCost`, which reads the same `prices.json` table and matches a family the same way (`model` contains the family). A row with any unpriced model gets `cost: null`. Main's usage outside any task becomes an `outside a task` row.
- The dashboard's ticket spend (`dashboard/spend.ts` `recordSpend`) takes `total` as a session's cost and sums the rows' `tokens`. The page shows a `null` row cost as `–`, and a task's or the chart's cost as `–` when any row under it is `null`.
- `docs/compatibility.md`: G9 says Cursor rows have no tokens or cost; the Local dashboard cells for Cursor say no gantt rows or spend; the install note (line 46) says no tokens or spend.

## Design

### 1. `agent_usage.py --cursor-agent <id>`

A new mode that prints one Cursor agent's runs as JSON for the hook, reusing the store reading and the token split:

- Split `cursor_costs` in two: `cursor_tokens(u)` returns the billed kinds `{input, output, read, write}` (the rule that input excludes cache tokens lives only here), and `cursor_costs` prices that result. `read_cursor` and the report are unchanged in behavior.
- Move the per-store query out of `read_cursor` into a helper that both use, so the SQL and the read-only open exist once.
- `--cursor-agent <id>` (with `--cursor-projects`, default `~/.cursor/projects`) looks through every `*/sdk-agent-store/*/index.db` for that agent and prints `{"runs": [{"at": <ms since epoch>, "model": <str or null>, "input": n, "output": n, "read": n, "write": n}, ...]}` in turn order. Runs without `usage_json` are left out, as in the report.
- Exit 2 with a stderr line when the id fails `[A-Za-z0-9_-]{1,80}` (the hook's `snapshotName` rule), when no readable store has the agent (an unreadable store is ignored when another store has the agent, so one corrupt store never stops a thread from getting tokens), or when one of its runs cannot be parsed. Anything else exits 0. It writes nothing.

### 2. The mapping: `mods/agent-gantt/hooks/cursor.ts`

- `CursorState` gains `runs: CursorRun[] | null` (`null` until the store was read once). A saved state without it reads as `null`, so old state files keep working.
- `cursorSnapshot(state, payload, now, threadId, prices)` takes the price table (`null` when `prices.json` cannot be read). When `state.runs` is not `null` it builds the records' usage from the runs before calling `buildRows(records, [], prices, 'Cursor')`:
  - every run adds `{input, output, read, write_5m: write, write_1h: 0}` under its model to `main.usage`, so `modelCost` prices it as `cursor_costs` does;
  - a run also adds to the usage of the task whose start is closest to the run's `at` (ties go to the earlier task), chosen among tasks that have spans only, since a task with no spans has no row. With no such task the run stays in main's usage and shows on the `outside a task` row, as `buildRows` already does;
  - subagent records get no usage. With a price table their rows show `0` tokens and `$0.00`; their work is counted in the turn that started them.
  - the snapshot `total` is the sum of the row costs, or `null` when any row's cost is `null`.
- With `state.runs` `null` the snapshot is what it is today: `0` tokens, `cost: null`, `total: null`.
- A run whose model has no family in `prices.json` makes its task's cost `null`, shown as `–` like any unpriced Claude Code row, and the snapshot `total` `null`. Its tokens still count.

### 3. The hook: `agent-team/scripts/cursor_gantt_hook.ts`

- On `stop`, `subagentStop` and `sessionEnd`, it runs `python3 -I <hook folder>/agent_usage.py --cursor-agent <session key>` with a 3 second timeout. It makes this read once, before taking the conversation lock, so the 3 second call does not hold the lock. Exit 0 with a `runs` list of the right shape is the read. Any other result (exit 2, timeout, no `python3`, bad JSON) is a failed read (`null`) and keeps the saved state's runs, so a store that cannot be read leaves the rows as they were and never fails the hook. A read with fewer runs than the saved ones never replaces them: the run store only grows, so a shorter read is an older one. The other three events do not read the store.
- It reads `prices.json` from its own folder (`~/.collective-wisdom/scripts/prices.json` once installed); a missing or bad file gives `null`.
- The session key is the one `snapshotName` already accepted, so the id passed to Python is safe.

### 4. Docs

- `docs/compatibility.md`: the Local dashboard cell for Cursor becomes partial only for what is still missing (see Not proven); G9 says Cursor rows get tokens and cost from Cursor's run store through `agent_usage.py`, that subagent rows show none of their own, and that Codex and Antigravity threads still write no snapshots. The install note (line 46) drops "no tokens or spend".
- `agent_usage.py`'s docstring gains the `--cursor-agent` line.

## Tests

- `test_agent_usage.py`: one table over `--cursor-agent` with the existing `cursor_store` fixture: an agent with priced and unpriced runs prints its runs in turn order with input net of cache; a run without usage is left out; an id in no store, a store that is not a database, and a bad `usage_json` exit 2; a bad id exits 2.
- `cursor.test.ts`: one table over states with runs: two prompts each get their run's tokens and cost, and `total` is their sum; a run 3 seconds before its prompt lands on that prompt's task; a run with no task gives an `outside a task` row; an unpriced model gives that task `cost: null` and `total: null` with tokens kept; `runs: null` gives today's rows; a subagent row gets `0` tokens. The existing case keeps checking `0` tokens and `null` cost with no runs.
- `cursor_hook.test.ts`: the existing table gains a `stop` case in a scratch `HOME` with a store holding `c1`'s run, checking the snapshot's task tokens and `total`, and a `stop` case with an unreadable store that exits 0 and keeps the rows.

## Leaves out

- Ticket spend with an unpriced Cursor session. `spendByTicket` adds only sessions with a `total`, so such a ticket's dollars leave the Cursor session out and its tokens include it. The usage report (`agent_usage.py --ticket`) still says `cost unknown`. Changing the ledger is a separate ticket if wanted.
- Subagent tokens and cost on their own rows. Cursor records none.
- Porting the `agent-gantt` and `status-pane` panes into Cursor (G10), Codex and Antigravity threads, and installing the `agent-gantt` plugin from `install.sh` (#282).
- The No Hands cost cap already counts Cursor through `agent_usage.py`; no change.

## Not proven before merge

- No Cursor thread runs the new code in this PR. Whether Cursor has written a run's `usage_json` by the time the `stop` hook fires is unknown. If not, a turn's tokens appear at the next `stop`, `subagentStop` or `sessionEnd`, and the last turn of a thread that ends without `sessionEnd` may never show them.
- The hook needs `python3` on the `PATH` Cursor gives hooks. Without it rows stay as today.
- The by-hand check pipes Cursor-shaped payloads into the hook with a scratch store and reads the snapshot; the live dashboard page is not opened.

## Calls I made

- **An unpriced Cursor model shows `–` on the row, not the words "cost unknown".** `–` is how the page already marks any row with no price, and it is not `$0`. A task, the chart's Total and the snapshot `total` go `–`/`null` with it.
- **Ticket spend with an unpriced Cursor session leaves its dollars out** (see Leaves out), because the ledger sums only sessions with a `total`. This is the existing rule for unpriced Claude Code sessions too.
- **The hook calls `agent_usage.py` instead of reading SQLite in Node.** The ticket asks to reuse the reading code, and the store query and the token split stay in one place. Pricing uses `prices.json` through `rows.ts` `modelCost`, the code the Claude Code gantt rows use, fed the token split from Python, so the rates and the cache rule exist once each.
- **The store is read only on `stop`, `subagentStop` and `sessionEnd`**, the events after which usage can change, to keep the other hooks fast. The runs are kept in the hook state, so every snapshot carries the last good read.
- **A failed read keeps the last good runs**, not zero. A thread whose store was never readable shows rows as today.
- **The store is read before the conversation lock, and the longer list of runs wins.** The read can take up to 3 seconds, so it happens before the lock and the lock is held only to apply the event and write. Two hooks can then finish out of order, so a read with fewer runs than the saved ones is dropped: the store only grows, so a shorter list is an older read.
- **Runs go to the task whose start is closest in time**, not by turn number. The hook may miss prompts (installed mid-thread), and on the trial repo the run began 3 seconds before the hook saw the prompt.
- **Subagent rows show `0` tokens and `$0.00`**, not `–`, so a task's cost is not blanked by subagents whose work Cursor counts, if at all, in the parent turn.
- **The snapshot `total` is the sum of the row costs.** Cursor reports no total of its own, so the page's "Claude Code reports" note never shows for a Cursor session.
- **`python3 -I` with a 3 second timeout**, inside the hook's existing 5 second Cursor timeout. `agent_usage.py` runs on the machine's Python 3.9.
- **`--cursor-agent` scans every Cursor project's stores** rather than guessing the project folder from the workspace path, since Cursor shortens long worktree folder names.
