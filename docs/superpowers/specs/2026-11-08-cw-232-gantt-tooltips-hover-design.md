# CW-232: Make the gantt tooltips show on hover in the dashboard

**Status:** Shipped
**Shipped:** in PR #236, as specified
**Ticket:** [#232](https://github.com/collective-wisdom-org/collective-wisdom/issues/232)
**Related:** CW-225 (bar tooltips, PR #228), #230 (old `app.js` in an open tab), #227 (ticket details, also edits `app.js`).

## Goal

Hovering a bar or a row in an open gantt chart for about a second shows its tooltip, including a bar of a task that is still running.

## Today

Facts from `main` at `d918a2b`.

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` puts a native `title` on each `.bar` (from `bars()`) and on each `.grow` row (from `rowTitle`).
- `draw` runs from `setInterval(draw, 1000)` and from every poll. For every open chart it sets `body.innerHTML = renderGantt(...)` on `.chart-body[data-ticket]` and `.chart-body[data-merged]`, changed or not.
- That replaces the element under the pointer every second, and the browser restarts its tooltip delay (about a second) on the new element, so the tooltip never shows.
- `drawMerged` already writes only when its html differs from `shownMerged`. The charts have no such guard.
- A running bar ends at `now`, so its `style` width changes every second. Its `title` also changes every second, because it includes the bar's duration (`<start>, running · <duration> · <model>`).
- `rowTitle` reads `<start>, running` for a running row, so a row's `title` does not change every second. The row's duration cell (`.num.dur`) does.
- `draw` lives inside the `typeof document !== 'undefined'` block, so `app.test.js` cannot call it.

## Design

1. **Skip unchanged charts.** Move the chart loop out of the browser block into an exported `drawCharts(root, data, now, apply)`:
   - It finds the `.chart-body[data-ticket]` and `.chart-body[data-merged]` bodies with `root.querySelectorAll`, renders each with `renderGantt` as today, and calls `apply(body, html)` only when `html` differs from the html last written to that body.
   - The last html per body is kept in a module-level `WeakMap` keyed by the body element. A body rebuilt by `renderStatus` or `renderMerged` is a new element, so its first draw always writes.
   - The browser's `draw` becomes `drawCharts(document, last, Date.now(), patchChart)`.
2. **Update a changed chart in place.** `patchChart(body, html)` parses `html` in a `<template>` and walks the old and new trees together:
   - Two elements with the same tag and the same number of child nodes are kept: the old one takes the new one's attributes (set the changed ones, remove the missing ones), and its children are walked the same way.
   - Two text nodes are kept, with the new text.
   - Anything else (a tag differs, the child count differs, a node type differs) is replaced by the new node, and its subtree is not walked.
   - An empty body (first write) just gets `innerHTML`.

   So a tick that only moves a running bar's width, or a duration cell's text, keeps every element, and the hovered bar or row stays the same element. When a task or a span is added, the changed part is replaced and the rest is kept.
3. **Stable title on a running bar.** A running bar's `title` drops the duration: `<name>` then `<start>, running · <model>`. A finished bar keeps `<start> to <end> · <duration> · <model>`. A running bar's `title` then changes only when the bar stops running, and a native tooltip is not disturbed by a text change every second. The bar's running length is still on the row's duration cell.

## Tests

In `agent-team/scripts/dashboard/page/app.test.js`, one table-driven case for `drawCharts` with fake bodies (`dataset`, plus a spy `apply`) under a fake `root`:

- Two calls with the same data and `now`, for a ticket chart and a merged chart of finished tasks: `apply` runs once per body.
- A second call with a later `now` on a running task: `apply` runs again for that body.
- A body whose ticket or merged id is missing from the data: `apply` never runs.

The test fails on today's code (there is no exported `drawCharts`, and today's loop writes every body on every call) and passes after the fix.

Update the existing bar tooltip case from CW-225 to the new running-bar text.

`patchChart` needs a real DOM, which `node --test` does not have, and it is a small UI interaction (`AGENTS.md` § Testing), so it gets no unit test. The PR's proof checks the hover by hand in a browser.

`node --test agent-team/scripts/dashboard/page/app.test.js` passes, and so does the full `node --test` line from `AGENTS.md` § Workflow.

## Non-goals

- A custom tooltip element (see Calls I made).
- Reloading a tab that runs an old `app.js` (#230).
- The details section on each ticket (#227). It also edits `app.js`; a merge conflict is expected, not a dependency.
- Any change to `renderStatus`, `renderMerged`, the poll, or the snapshot data.

## Calls I made

- **The running bar's tooltip loses its live duration.** The ticket doesn't ask for this. Without it the hovered bar's `title` changes every second, and a native tooltip may hide or never show when its text changes under the pointer. The duration is still in the row's duration cell.
- **In-place update, not a custom tooltip.** The ticket allows either. The in-place walk is about 25 lines, keeps the native tooltip, and adds no CSS or pointer handlers. A custom tooltip would need positioning, styling and its own hover logic.
- **A generic tree walk, not bar-specific code.** It keeps rows and duration cells too, so nothing in a chart is replaced on a tick that only changes numbers.
- **The last html per body lives in a `WeakMap`**, so a rebuilt status or merged list starts fresh with no cleanup code.
- **`patchChart` has no unit test**; the guard has one. The hover itself is checked by hand.
