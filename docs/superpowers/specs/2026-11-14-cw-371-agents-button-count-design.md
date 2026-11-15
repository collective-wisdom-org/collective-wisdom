# CW-371: Count every subagent in the dashboard Agents button

**Status:** Shipped
**Shipped:** in PR #393, as specified
**Ticket:** [#371](https://github.com/collective-wisdom-org/collective-wisdom/issues/371)
**Runs beside:** CW-370 (in progress), which edits the same row markup and keeps the footer's Agents control. This change stays inside `panelSwitch`, `summaryLine` and the count helpers, so whoever builds second has a small rebase.

## Goal

A card shows its agent count once, on the `Agents` button, and that number counts every task and every subagent under it. The footer summary keeps only the time and the cost.

## Today

Facts from main at `4b974cb`, all in `agent-team/scripts/dashboard/page/app.js`.

- `panelSwitch` labels the button `Agents <span class="pill">n</span>` with `n = taskCount(gantt)`. `taskCount` is `ganttTasks(sessions, 0).length`: top-level tasks only, no `kids`.
- `summaryLine` draws `5 agents · 9m 44s · $2.02`. The count is `ganttSummary(...).agents`, which is `items.reduce((n, i) => n + 1 + i.kids.length, 0)`: tasks and subagents. So the two numbers differ.
- `panelSwitch` draws the button on ticket cards and rows, merged rows (`renderMerged`) and project manager rows.
- The 5-second live update rewrites each `.summary[data-ticket]` span from `summaryLine`.
- `drawStatus` rebuilds the cards only when its JSON key changes. The key maps each `gantt` to `[session ids, taskCount(gantt)]`, so the pill is redrawn when the task count moves.

## Design

### `app.js`

- `taskCount(sessions)` returns tasks plus subagents: `ganttTasks(sessions, 0).reduce((n, i) => n + 1 + i.kids.length, 0)`. It is the one place the count is computed.
- `ganttSummary` drops its `agents` field and returns `{ ms, cost }` (still `null` when nothing is drawn). Nothing else reads `agents`.
- `summaryLine` builds its line from the time and the cost only: `9m 44s · $2.02`. A missing cost is still left out. It still returns `''` with no Gantt.
- `panelSwitch` is unchanged: it already calls `taskCount`, so ticket, merged and project manager buttons all get the new count, and `Agents 0` stays disabled when nothing is drawn.
- `drawStatus` keeps calling `taskCount` in its key. With the new count, a new subagent now rebuilds the card so its pill moves. That rebuild is the only behavior change outside the label and the summary.
- The `taskCount` and `summaryLine` doc comments say what they now count and show.

### `app.test.js`

- The footer summary test: `ganttSummary` returns `{ ms, cost }`, and the drawn summary for one task and one subagent is `3m 00s · $1.50`.
- One table-driven test of the button count over `renderStatus` (ticket card), `renderMerged` (merged row) and `renderChief` (project manager row), each fed a Gantt of 2 tasks and 3 subagents: the button reads `Agents 5`. A row with no tasks reads `Agents 0` and is disabled.
- The live update path calls the same `summaryLine`, so the summary test covers it.

### `README.md`

The dashboard paragraph changes "an `Agents` count of tasks" to "an `Agents` count of tasks and their subagents", and the footer example from `3 agents · 41m 05s · $2.10` to `41m 05s · $2.10`.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `taskCount` counts subagents; `ganttSummary` drops `agents`; `summaryLine` drops the count. |
| `agent-team/scripts/dashboard/page/app.test.js` | Update the summary test; add the button count table. |
| `README.md` | Dashboard paragraph: the count and the summary example. |

## Non-goals

- The `Details` panel's session, task and subagent counts.
- Anything the Gantt chart draws.
- Other footer or row markup (CW-370's).

## Calls I made

- **A new subagent now redraws the card.** The rebuild key uses `taskCount`, so with subagents counted a card rebuilds when one starts, the same way it does today when a task starts. Without that the pill would lag. The open panel and the page position already survive a rebuild.
- **`ganttSummary` loses its `agents` field** instead of keeping an unused number beside `taskCount`, so there is one count to keep right.
- **The count lives in `taskCount`** (renamed in meaning, not in name). Renaming it would touch more lines that CW-370 may also touch.
- **The summary keeps its separator rules:** with no cost it is just the time; with no Gantt it is empty and the span is not drawn, as today.
- **The `Agents` pill on a running ticket helper card** gets the new count too. It goes through the same `panelSwitch`.
