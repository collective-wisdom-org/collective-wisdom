# CW-216 plan: agent gantt waterfall by task

Spec: `docs/superpowers/specs/2026-11-08-cw-216-gantt-waterfall-design.md` (approved). Test command for this PR:
`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: preamble and task name (`mods/agent-gantt/hooks/timeline.ts`)
- `PREAMBLE` matches `Act as the … agent|sub-agent|subagent for this task`.
- `taskName` drops a leading `TEAM MODE.` from the kept line (if nothing is left, keep looking at the next line).
- Test (`timeline.test.ts`): one table for `taskName`.

## Task 2: approval waits are not working time
- Pure helper in `timeline.ts` for wait counting (open/close waits per agent id with overlap, an agent that ended mid-wait stays closed), moved out of `pauseWhile` in `register.tsx`; `pauseWhile` calls it.
- `register.tsx`: add `ExitPlanMode` to the `pauseWhile` tool list; add a `tool.check` hook that awaits `next(e)` and, when `decision === 'ask'` and `e.approver` is set, starts a wait for the agent (`e.agentId`) keyed by `tool_use_id`; a `tool.call` hook on every tool ends the wait for its `tool_use_id` when `next(e)` settles (also in `finally`). An ask without `approver` is not a wait.
- Test (`timeline.test.ts`): one table with a fake clock: permission ask, plan approval, overlapping waits, agent ends mid-wait; assert no span covers the wait.

## Task 3: rows without the duplicate (`rows.ts`)
- `buildRows` emits no `session` row. If main's cost/tokens exceed the sum of its task rows, emit one depth 1 task row `outside a task` with the difference (cost null stays null). Keep `Row.kind` type unchanged (old snapshots still carry `session`).
- Update `rows.test.ts`: no session row; one task gives main's work once; usage outside any task gives the extra row.

## Task 4: page waterfall (`agent-team/scripts/dashboard/page/app.js`, `index.html` CSS)
- `renderGantt(sessions, now)`: merge all sessions' rows into one chart. Top-level items: each `task` row and each depth 1 `agent` row, with deeper rows nested. Drop a `session` row when its session has task rows; else treat it as a task.
- Active axis: union of all working spans of all rows (open spans end at `now`, or `updatedAt` when the session is stale); a time maps to active ms before it; gaps take no width.
- Each top-level row: name, bar, active duration (union of own and descendants' spans, `9m 12s` style), cost (own + descendants; dash if any unknown). Nested rows: own duration and cost, indented, muted. Model, tokens, harness, worktree, clock range go in the row `title`.
- Last line: total active time and sum of top-level costs; a note `Claude Code reports $X for these sessions. Row costs use prices.json.` when every session has a numeric `total` and their sum differs from the row sum by >= $0.01. Stale styling kept.
- The `Agents` pill (cards and merged rows) counts top-level tasks via the same helper.
- Test (`app.test.js`): one table for `renderGantt`: sessions merge in start order; idle gap takes no width; subtotals include subagents and parallel subagents count once; total is the sum; note only when totals differ; old `session` row not drawn when tasks exist; pill counts tasks.

## Task 5: cost difference
- Compare row costs of a real snapshot in `.agent-team/gantt/` of the root checkout (read only, `/Users/david_beallor/Documents/collective-wisdom`) with its `total`; record the cause in `docs/superpowers/as-built/2026-11-08-cw-216-gantt-waterfall.md` (use the as-built template from superpowers-project-memory). Fix a mod pricing bug here if that is the cause; else leave the note as the handling.
- As-built also states whether T3 approvals reach `tool.check` as an `ask` with `approver` (not proven without a real run).
