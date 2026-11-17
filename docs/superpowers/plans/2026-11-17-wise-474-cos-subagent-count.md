# WISE-474 plan: show the subagent count next to the Chief of Staff dashboard tab

Spec: [../specs/2026-11-17-wise-474-cos-subagent-count-design.md](../specs/2026-11-17-wise-474-cos-subagent-count-design.md)

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`

## Task 1: `app.js` and `index.html`

- Add `export const subagentCount = (sessions) => ...` next to `taskCount`: the rows with `kind === 'agent'` among `ganttTasks(sessions, 0)` items and their kids; 0 for a missing or empty list.
- `renderDetails` uses `subagentCount(r.gantt)` instead of its inline `drawn.filter(...)`; its output is unchanged.
- `index.html`: the `tab-cos` button gets `<span class="pill tab-count" data-count="cos" aria-hidden="true"></span>` after its text.
- `TAB_LABELS` gains `cos: 'Chief of Staff'`; `drawTabCounts` uses `{ ...tabCounts(last.status, last.merged), cos: subagentCount(last.chief?.gantt) }`. Update the comment above it to name the Chief of Staff tab.

## Task 2: one table-driven test

In `app.test.js`, one test over `subagentCount`: `undefined`, `[]`, a session with only `task` rows (0), and two sessions with depth-1 and depth-2 `agent` rows (several). Import it in the existing import line.

## Task 3: docs

README § Local dashboard: the count pill line names the Chief of Staff tab too (subagents in its session's chart); the accessible name example stays.
