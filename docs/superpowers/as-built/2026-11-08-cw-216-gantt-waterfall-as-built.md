# As-built: Agent gantt as a waterfall by task, with active time only

**Shipped:** 2026-11-08 in the CW-216 PR (number added when it opens)
**Ticket:** CW-216
**Spec:** [2026-11-08-cw-216-gantt-waterfall-design.md](../specs/2026-11-08-cw-216-gantt-waterfall-design.md)
**Plan:** [2026-11-08-cw-216-gantt-waterfall.md](../plans/2026-11-08-cw-216-gantt-waterfall.md)

## What shipped

The Agents chart under a status card and under a merged row is one waterfall per ticket. Rows are tasks in start order across the ticket's sessions. The axis is active time, so waiting takes no width. Each task row shows its active time and its cost with its subagents included, a total line is the sum of those rows, and a note shows the engine's figure when it differs.

## How it was built

1. `taskName` skips the `Act as the ... sub-agent for this task.` preamble and drops a leading `TEAM MODE.`.
2. Approval waits are not working time. A pure `createWaits` helper in `timeline.ts` counts overlapping waits per agent. `pauseWhile` uses it. A `tool.check` hook starts a wait when the verdict is `ask` and the input has an `approver` and a `tool_use_id`. A `tool.call` hook on every tool ends it when the call settles. `ExitPlanMode` joins the `pauseWhile` list.
3. `buildRows` emits no `session` row. Main's usage that no task row carries (before any task, or in a task with no spans) becomes one `outside a task` row.
4. `renderGantt` and the `Agents` pill share one merge (`ganttTasks`). `index.html` loses the per-session box styles.
5. Cache writes are priced at the 1h rate (see below).

## Differs from the spec

- `spend.ts` counted main's tokens from the `session` row. With that row gone, a new snapshot would have lost main's tokens in the ledger. It now takes the `task` rows as main's work when a snapshot has no `session` row, and keeps the old rule when it has one.
- The dashboard's snapshot reader fills an empty span list with one span from start to end, so the `outside a task` row reaches the page as a zero length span. It has a duration of `0s` and no visible bar, as intended.
- The page's change check for status cards now includes the task count, so the pill follows new tasks in a session that was already known.

## Why the costs differ

Compared one real snapshot of each kind in the root checkout's `.agent-team/gantt/` with its engine `total`, and priced the sessions' own transcripts (`~/.claude/projects/.../<session>.jsonl`) to see which side is right. There are three causes.

1. **Cache writes at the wrong rate (a mod bug, fixed here).** The mod priced every cache write at `write_5m`. `TurnUsage` has no 5m/1h split, and all 9.4M cache-write tokens across the transcripts checked were 1h entries (none were 5m). The engine's total matches prices.json with writes at `write_1h` to the cent on the four Opus sessions without subagents checked (for example $0.75, $1.09, $0.81, $1.21). `rows.ts` now uses `write_1h`.
2. **Sonnet cache reads (a data difference, not fixed).** For 42 Sonnet sessions whose mod tokens equal the transcript's, a least squares fit of the engine total gives cache reads at about $0.10 per million tokens and writes at about $4, while prices.json lists Sonnet reads at $0.20. The Opus rows show the engine uses prices.json's read rate there. So the Sonnet read rate in `prices.json` looks twice what the engine charges, which makes Sonnet rows about 1.5 times the engine total on cache heavy sessions (for example $5.52 against $3.58). This is the shared price table that `agent_usage.py` also reads, and I could not confirm the true price from here, so I left it. The page note is how it shows until someone checks the rate.
3. **Usage the mod had not seen.** Usage is added at `turn.complete`, so a subagent still in its first turn shows zero tokens, and a session the mod joined late is missing what came before (the snapshot of the session that built this had a running subagent at zero while the engine total was $2.43 against $0.93 in rows). The note covers this too.

## Verified

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.
- Task 5 numbers are from the read-only snapshot and transcript comparison above, not from a test.

## Known gaps / deferred

- Not proven without a real run: that T3 Code's approvals reach `tool.check` as an `ask` with `approver: 'host'`. The types say so and the tests use a fake clock. If they do not, an approval wait in a T3 session is still counted as working time, as before.
- The `ask` wait lasts until the call settles, so the tool's own run time after approval counts as waiting, as the spec chose.
- Stored history keeps its recorded spans, which may include old approval waits and the old `session` row. The page draws them by the same rules.
- The Sonnet read rate in `prices.json` needs a check against the provider's price list.

## Next

None. The spend ledger and the merged row's spend figure stay with CW-209.
