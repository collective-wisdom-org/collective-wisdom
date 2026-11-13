# CW-288: Attach a Cursor ticket helper's session to the ticket it filed

**Status:** Spec
**Ticket:** [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288)
**Related:** [#286](https://github.com/collective-wisdom-org/collective-wisdom/issues/286) (helpers on the Ship loop tab, PR #289), [#284](https://github.com/collective-wisdom-org/collective-wisdom/issues/284) (Cursor gantt spend), [#258](https://github.com/collective-wisdom-org/collective-wisdom/issues/258) (Cursor gantt snapshots)

## Goal

A ticket helper run on Cursor behaves on the dashboard like one run on Claude Code: while it runs it is a placeholder card titled with its request line, and once it files a ticket its session sits in that ticket's gantt before Spec and its tokens (and cost, when priced) count in the ticket's spend.

## Depends on CW-286

This builds on CW-286 (spec `docs/superpowers/specs/2026-11-13-cw-286-helpers-on-ship-loop-design.md` and PR #289 on `feat/cw-286-helpers-on-ship-loop`, not merged when this spec was written). The build starts only after #289 merges, and builds on `main`. It relies on these parts of CW-286, read at `601f805`:

- `pickFiledTicket(answer)` and `pickRequest(text)` in `mods/agent-gantt/hooks/snapshot.ts`. This ticket imports them; it does not copy them.
- `buildSnapshot`'s optional `ticket` and `request` arguments, written as snapshot fields (null when left out).
- `cleanTeamSnapshot` reading `ticket` (only as `<prefix>-N`) and `request`, `ledgerSessions` returning a root `TICKET HELPER` session with a ticket, the `Writing tickets` placeholder for a running helper with no ticket, and the rule that a finished helper with no ticket shows nowhere (`agent-team/scripts/dashboard/api.ts`). The running test already counts a Cursor snapshot with an open main span as running, so the dashboard needs no change here.

If #289 merges with any of these renamed or changed, the build follows what merged and says so in the as-built.

## Today

- The Cursor hook (`agent-team/scripts/cursor_gantt_hook.ts`, rules in `mods/agent-gantt/hooks/cursor.ts`) runs on six events and keeps a `CursorState` per conversation. `cursorSnapshot` calls `buildSnapshot` without `ticket` or `request`, so with CW-286 a Cursor helper's placeholder has an empty title and its session never attaches to a ticket.
- None of the six events carries the assistant's text. `afterAgentResponse` is not registered (CW-258 left it out).
- On `stop`, `subagentStop` and `sessionEnd` the hook runs `agent_usage.py --cursor-agent <id>` (CW-284), which prints `{"runs": [...]}` from the runs with `usage_json` in Cursor's run store. It does not read the `result` column.
- What the run store holds, checked on this machine's stores (`~/.cursor/projects/*/sdk-agent-store/*/index.db`, 11 runs): a `FINISHED` run's `result` is the run's whole final reply (853 to 3668 characters, from its first word to its last); a `CANCELLED` or `ERROR` run has an empty `result` and no usage. No ticket helper has run on Cursor on this machine, so no `result` with a `TICKET HELPER DONE` block was seen.

## Design

### 1. Source of the text: the run store's `result`

The hook reads the helper's final text from the run store, not from an `afterAgentResponse` hook. Reasons:

- The run store is already read on `stop`, `subagentStop` and `sessionEnd`, and its `result` is shown above to hold the final reply of a finished run.
- `afterAgentResponse` would be a seventh event in `~/.cursor/hooks.json`, which means an `install.sh` change, and no Cursor hook has yet been seen firing in a T3 Cursor thread (G9), so it would add an unchecked path to an unchecked one.

The build checks a real Cursor ticket helper run if one exists on the machine by then (a `TICKET HELPER DONE` block in a `result`). If none does, the PR lists it under Not proven and says which source was used and why.

### 2. `agent_usage.py --cursor-agent`

- The output gains `results`: the non-empty `result` text of each of the agent's runs, in turn order, from every run (not just those with `usage_json`). `runs` is unchanged.
- The `result` column is read only for this mode. `read_store`, `read_cursor` and the report keep their behavior and output.
- A store that has no `result` column gives `results: []`.
- The exit rules are unchanged: no readable store with the agent still exits 2.

### 3. State and snapshot (`mods/agent-gantt/hooks/cursor.ts`)

- `CursorState` gains `ticket: string | null` and `request: string | null`, null in `emptyState`. A state saved before this change reads as null for both.
- On `beforeSubmitPrompt`, when the prompt sets the heading (the first prompt) and the heading is `TICKET HELPER`, `request` is `pickRequest(prompt)`. It is never changed after.
- A new pure function, `withFiledTicket(state, results)`, returns the state with `ticket` set when the heading is `TICKET HELPER`, `ticket` is still null, and `results` is a list: the first `pickFiledTicket(text)` that is not null, over the texts in turn order. Anything else (results null, no block, `Tickets: none`, a set ticket) gives the state back. So the ticket is the first `<PREFIX>-N` on the `Tickets:` lines and never changes once set.
- `cursorSnapshot` passes `ticket` and `request` to `buildSnapshot`.

### 4. Hook (`agent-team/scripts/cursor_gantt_hook.ts`)

- `readRuns` also returns `results` when the output has a `results` list of strings; anything else counts as no results, and the runs are still taken.
- After `applyEvent` and the runs, the hook applies `withFiledTicket` with the results of this event's read (null when it did not read or the read failed). The results are not saved in the state file; only the ticket is.
- A store that cannot be read, a timeout, an empty `result` or a `result` with no block leaves `ticket` null and the hook still exits 0, as today.

### 5. Docs

- `docs/compatibility.md` G9: a Cursor ticket helper's snapshot carries its request line and, from the run store's `result`, the ticket it filed, so its session attaches to that ticket like a Claude Code helper's; that this has not been seen in a real Cursor helper run (unless the build saw one).
- README.md § Local dashboard: the CW-286 text does not say a Cursor helper is left out, so no change is expected. If the merged text says so, that line is fixed.

## Leaves out

- Claude Code helpers (CW-286), Codex and Antigravity helpers.
- An `afterAgentResponse` hook and any `install.sh` change.
- Backfilling Cursor helper sessions already on disk.
- Any dashboard (`api.ts`, `app.js`) change: CW-286 already handles a root helper snapshot with `ticket` and `request` the same way whichever harness wrote it.
- Waiting or retrying when the run store has not written a turn's `result` by `stop`.

## Calls I made (surprising first)

- **The run store's `result`, not `afterAgentResponse`.** Seen holding finished replies on real Cursor runs here, already read on the right events, and needs no new hook in `~/.cursor/hooks.json`. No real Cursor helper run exists on this machine to check against, and a child cannot start one, so unless one appears before the build, the PR lists it under Not proven.
- **No retry if `result` is late.** If Cursor has not written the final turn's `result` when `stop` fires and `sessionEnd` does not fire, the helper's ticket stays null and the session attaches to nothing (the placeholder still goes away). CW-284 has the same open question for usage. A retry or delay in the hook adds latency to every Cursor turn.
- **Every run's result, not only the last.** The block can only be in the final reply, but a helper may take more than one turn; taking the first block in turn order matches the Claude rule ("first one found stays").
- **`results` read from every run, not just runs with usage**, so a finished run whose usage has not landed still gives its text.
- **The results text is not kept in the state file**, only the ticket: it keeps the state small and the text off disk beyond what Cursor already keeps.
- The dashboard is left alone: CW-286's code does not care which harness wrote the snapshot.

## Tests

- `mods/agent-gantt/hooks/cursor.test.ts`: one table for `withFiledTicket` mapping run store results to the snapshot's `ticket`: one ticket, several (first wins), `Tickets: none`, no block, an errored run (no results, `[]`), an unreadable store (`null`), a ticket already set (kept), a non-helper heading (stays null). The same table, or one row beside it, checks `request` from the first `TICKET HELPER` prompt and that both reach `cursorSnapshot`'s JSON.
- `agent-team/scripts/test_agent_usage.py`: the existing `--cursor-agent` table gains `results` in its expected output, including a run with an empty `result` left out.

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` pass. A real Cursor helper run attaching to its ticket on the dashboard goes under the PR's Not proven unless the build sees one.
