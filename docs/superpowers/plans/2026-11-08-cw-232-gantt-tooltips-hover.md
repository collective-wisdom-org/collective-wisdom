# CW-232 plan: gantt tooltips on hover

Spec: `docs/superpowers/specs/2026-11-08-cw-232-gantt-tooltips-hover-design.md`. All edits in `agent-team/scripts/dashboard/page/`.

## Task 1: stable running-bar title (`app.js`, `app.test.js`)

- In `bars()`, a running bar's `meta` leaves out `duration(b - a)`: title is `<name>\n<start>, running · <model>`. A finished bar keeps `<start> to <end> · <duration> · <model>`.
- Update the CW-225 case (line ~155-160 of `app.test.js`): the running bar's title is `...\n\d\d:\d\d, running · opus-5-5`.
- Check: `node --test agent-team/scripts/dashboard/page/app.test.js`.

## Task 2: `drawCharts` guard (`app.js`, `app.test.js`)

- Add module-level `const shownCharts = new WeakMap()` and exported `drawCharts(root, data, now, apply)`:
  - for each `root.querySelectorAll('.chart-body[data-ticket]')`, look up `data.status.flatMap(g => g.rows)` by id; for each `.chart-body[data-merged]`, look up `data.merged` by id; skip a body with no entry;
  - `html = renderGantt(entry.gantt, now)`; if `shownCharts.get(body) !== html`, `shownCharts.set(body, html)` and `apply(body, html)`.
- Test first (must fail on `main`): table-driven, fake `root` whose `querySelectorAll` returns fake bodies `{dataset}` by selector, spy `apply`. Rows: same data twice with finished tasks, `apply` once per body; later `now` with a running task, `apply` again; id missing from data, never applies.

## Task 3: `patchChart` and wiring (`app.js`)

- Add `patchChart(body, html)` (browser use, not exported-tested): empty body, or `body.innerHTML === ''`, gets `innerHTML = html`. Otherwise parse html in a `<template>` and `patchNode(body, template.content)`, which walks children pairwise: same node type and tag (and, for elements, same child count) keeps the old node, syncs attributes (set changed, remove missing) and recurses; text nodes copy `nodeValue` when different; otherwise `old.replaceWith(new)`. Extra or missing trailing children: append or remove.
- Inside the browser block, `draw = () => { if (last) drawCharts(document, last, Date.now(), patchChart) }`; delete the old loop.
- `patchChart` also sets `shownCharts` implicitly via `drawCharts`; nothing else.

## Verify

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`
- By hand (PR proof): serve the dashboard, open a chart with a running task, hover a bar and a row for 1.5 s, see the tooltip. If no browser is available, say so under Not proven.
