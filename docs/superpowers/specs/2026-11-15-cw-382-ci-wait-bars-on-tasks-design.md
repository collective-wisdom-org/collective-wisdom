# CW-382: Draw each CI wait bar on the task row that was waiting for it

**Status:** Shipped
**Ticket:** [#382](https://github.com/collective-wisdom-org/collective-wisdom/issues/382)
**Shipped:** in PR #397, as specified

## Goal

CW-365 drew the PR's CI wait as blue bars on a separate `CI wait` row below `Total`. Draw each CI bar on the track of the task that was waiting for it instead, so a task's green working bars and blue CI bars sit side by side on one track, and drop the `CI wait` row.

## Today

- `ciWait` in `agent-team/scripts/dashboard/ci.ts` gives the PR's CI spans as `[start, end | null]`. They reach the page as `ci`; `ciSpansOf` in `page/app.js` closes an open end at `now` and marks it open. A span names no task.
- `renderGantt` builds the axis from the working spans and the CI spans (CW-365), and `ciRow` draws every CI span on one `CI wait` row after `Total`, with a row tooltip (commit count and clock range) and one blue bar per merged span.
- Task rows come from `ganttTasks`; `line()` draws one `.track` per row with green `.bar` working spans from `bars()`. Subagent rows (`kids`) draw under their task.
- `page/index.html` styles the CI row with `.grow.gciwait` (amber duration while running, `--accent` bars).

## Design

### 1. Which task owns a CI span (`ciOwner` in `page/app.js`)

A new pure function picks, for each CI span, one of the top-level tasks `ganttTasks` returns:

- The owner is the task whose latest finished working span ends at or before the CI span's start, taking the task with the latest such end. That is the task that most likely pushed the commit CI ran on.
- A working span counts as finished when it has an end that is not the open running end. A task still running when CI starts does not qualify through its open span, only through spans it already finished. A stale session's open span counts as finished, because its end is closed at the session's last update.
- Only the task's own spans count, not its subagent rows'. A subagent's work sits inside its task's span.
- Ties go to the task that started first (the earlier one in `ganttTasks` order).
- If no task qualifies (CI started before any task finished a span), the earliest task owns the span.

It is exported for the test.

### 2. Drawing (`renderGantt`)

- Each task's CI spans are merged (overlapping spans from a push that cancelled a run draw as one bar) and drawn on that task's `.track`, before its working bars (so work done during the wait stays on top), as `<span class="bar ci" ...>` with `left` and `width` from the same `place(a, b)`, at least 0.5% wide.
- Each CI bar keeps CW-365's tooltip: `CI wait`, then `<start> to <end> · <duration>`, or `<start>, running · <duration so far>` while open. It never carries the `running` class, so an open span stays blue, not amber.
- Merging is per task: a span merges only with other spans of the same task. Two tasks' spans never share a bar.
- `ciRow` and the `CI wait` row are removed. The row tooltip with the commit count goes with it.
- What stays: the axis (working spans plus CI spans), the `Total` row, every row's duration and cost (working spans only), `ganttSummary`. With no CI spans the chart html is the same as today.

### 3. Styles (`page/index.html`)

- `.grow.gciwait.running .dur` and `.grow.gciwait .bar` go.
- `.bar.ci { background:var(--accent); }` replaces them. `--accent` already switches for light and dark mode. A stale task's track is dimmed as today, CI bars included.

### 4. Tests (`page/app.test.js`)

Replace the CW-365 CI test with:

- One table-driven test of `ciOwner`: a span in the gap after task A ends while B has not started goes to A; a span that starts while a later task B is running goes to A (B's open span does not count); a span still running at `now` goes to the task that finished last before it; a span before any task finished goes to the earliest task.
- One test of `renderGantt`: the CI bar is on its owner's track with the expected `left` and `width` on the combined axis, has class `bar ci` and not `running`; there is no `CI wait` row; every row's duration and cost and the `Total` row are the same with and without CI spans; with no CI spans the html equals `renderGantt(sessions, now)`.

### 5. Docs

`README.md` § Local dashboard: the chart sentence says CI wait draws as blue bars on the track of the task that waited for it, still left out of every duration and the total.

## Leaves out

- The agent-gantt mod pane and the Cursor hook. They have no CI data.
- Adding CI time to a task's duration or cost.
- Review wait and merge-approval wait.
- Any change to how CI spans are read (`ci.ts`, `api.ts`).

## Calls I made (surprising first)

- **The chart loses the commit count and the total CI wait.** The `CI wait` row's tooltip (`N commits ran CI · start to end`) and its merged duration go with the row. Each blue bar still shows its own clock range and duration on hover.
- **I kept the ticket's owner rule: the task that last finished a working span before CI started.** It matches "the task that pushed the commit". I found no rule that reads better, so the PR will say the rule stayed.
- **A task still running when CI starts doesn't own the span through that run.** Its open span has no end yet, so it can't have pushed before CI started. If it finished an earlier span before CI started, that span still counts.
- **Only the task's own spans pick the owner, not its subagents'.** A subagent works inside its task, so the task's span covers it.
- **CI bars on a task row merge only with that task's other CI spans.** Two tasks' CI never share one bar.
- **A ticket with CI but no task finished yet gives the CI to the earliest task**, as the ticket says.
- **CI bars use a new `ci` class on `.bar`** instead of a row class, since the row now mixes green and blue bars.
- **One README sentence changes**, though the ticket names no doc.

## Touches

None of: data, money, auth, user email, migrations.
