# WISE-474: Show the subagent count next to the Chief of Staff dashboard tab

**Status:** Shipped
**Ticket:** [#474](https://github.com/collective-wisdom-org/collective-wisdom/issues/474)
**Shipped:** in PR #475, as specified

## Goal

The Chief of Staff tab on the local dashboard carries a count pill, like the Ship loop, Backlog and Done tabs, showing how many subagents the Chief of Staff session has. You can see the number without opening the tab.

## Today

- `agent-team/scripts/dashboard/page/index.html`: the Ship loop, Backlog and Done tab buttons each end with `<span class="pill tab-count" data-count="..." aria-hidden="true"></span>`. The `tab-cos` button has only the text `Chief of Staff`.
- `agent-team/scripts/dashboard/page/app.js`:
  - `tabCounts(status, merged)` returns `{ ship, done, backlog }`.
  - `drawTabCounts` (inside the page's start-up code) walks every `[data-count]` pill, writes `counts[key] ?? 0` into it when it changed, and sets the button's `aria-label` to `` `${TAB_LABELS[key]}, ${n}` ``. `TAB_LABELS` has `ship`, `done` and `backlog`. It runs on every poll, apart from the card rebuilds.
  - `renderDetails` counts a ticket's subagents inline: `ganttTasks(r.gantt, now)`, flattened to tasks and their kids, then the rows with `kind === 'agent'`.
- `api.chief.gantt` (from `agent-team/scripts/dashboard/api.ts`) holds the Chief of Staff session's snapshots; it is empty or missing with no session in the last 24 hours.
- `README.md` § Local dashboard says the Ship loop, Backlog and Done tab labels carry a count pill.

## Change

1. `app.js`: add an exported `subagentCount(sessions)` that returns the number of rows with `kind === 'agent'` among the tasks `ganttTasks` builds and their kids, and 0 for a missing or empty list. `renderDetails` uses it instead of its inline filter, so there is one rule for "subagent".
2. `index.html`: the `tab-cos` button gets `<span class="pill tab-count" data-count="cos" aria-hidden="true"></span>` after its text, the same markup as the other three.
3. `app.js` page code: `TAB_LABELS` gains `cos: 'Chief of Staff'`, and `drawTabCounts` merges `cos: subagentCount(last.chief?.gantt)` into the counts. The existing loop then writes the pill and sets the button's accessible name to `Chief of Staff, N`. Nothing about the Chief of Staff card changes, so the pill updates on each poll without rebuilding the card.
4. `app.test.js`: one table-driven test for `subagentCount`: no sessions (`undefined` and `[]`), a session whose rows have no `agent` kind, and sessions with several subagents (a depth-1 agent row and depth-2 agent rows under a task, across two sessions).
5. `README.md` § Local dashboard: the count pill line names the Chief of Staff tab too, counting the subagents in the Chief of Staff session's chart.

## Not changing

- `tabCounts` and its `{ ship, done, backlog }` shape: it counts tickets from the status and merged lists, and its tests stay as they are.
- `taskCount` and the `Agents` pill on ticket cards and project manager rows, and the Details panel's wording.
- Counts for the project manager threads or ticket helpers.
- `api.ts` and the server: the count is worked out in the page from data it already gets.

## Acceptance

- With a Chief of Staff session whose chart has N subagent rows, the tab reads `Chief of Staff N` and its accessible name is `Chief of Staff, N`.
- With no Chief of Staff session, or one with no subagents, the pill shows `0`.
- The pill changes on the next poll after the snapshot changes, and the Chief of Staff card is not rebuilt for it.
- A ticket's Details panel still shows the same subagent count as before.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `subagentCount`, `renderDetails` uses it, `TAB_LABELS` and `drawTabCounts` |
| `agent-team/scripts/dashboard/page/index.html` | Count pill on the Chief of Staff tab |
| `agent-team/scripts/dashboard/page/app.test.js` | Table-driven test for `subagentCount` |
| `README.md` | § Local dashboard, the tab count line |

## Calls I made

- **A subagent is any `agent` row in the chart, the rule `renderDetails` uses today.** That includes the Chief of Staff's own Task-tool subagents (depth-1 agent rows) and the agents they start (depth 2 and below). Task rows (the user's prompts) are not counted, so the number is lower than the `taskCount` an `Agents` pill would show for the same session.
- **The count covers every session in `api.chief.gantt`**, not only the newest, because the tab's chart draws all of them.
- **`tabCounts` is left alone and the new count is a separate `subagentCount`.** Folding it into `tabCounts` would change that function's return shape and its existing test for no gain; `drawTabCounts` merges the two.
- **The pill shows `0` with no session**, matching the other tabs when empty, as the ticket asks.
- **README is updated** because it lists which tabs carry a count; no other living doc names the tab pills.
