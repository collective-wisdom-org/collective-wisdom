# CW-369 plan: collapsible top-level dashboard headers

Spec: `docs/superpowers/specs/2026-11-14-cw-369-collapsible-top-headers-design.md`

## Task 1: markup and state in `agent-team/scripts/dashboard/page/app.js`

1. Export `bandKey = (slug) => \`band:${slug}\``.
2. `renderStatus`: replace the `<section class="band band-<slug>"><h2>` wrapper with `<details class="band band-<slug>" data-band="band:<slug>"[ open]><summary class="band-head"><h2>name</h2></summary>…</details>`; `open` unless `collapsed.has(bandKey(slug))`. Signature unchanged.
3. `renderChief(api, page, open, size, collapsed = new Set())`: wrap `<h2>Project manager</h2>` and `pm.html` in the same `<details class="band band-pm" data-band="band:pm">`. The card stays outside. `drawCos` passes `readCollapsed()` to both `renderChief` calls.
4. Start-up: if `band:done` is in `readCollapsed()`, remove `open` from `details[data-band="band:done"]`.
5. The capture-phase `toggle` listener also handles `details[data-band]`, using `d.dataset.band` in the same array. Only `d.matches('details.group, details[data-band]')` toggles count; key is `data-group` or `data-band`.

## Task 2: `agent-team/scripts/dashboard/page/index.html`

1. Wrap `<h2>Done</h2>` and `<div id="merged">` in `<details class="band band-done" data-band="band:done" open><summary class="band-head"><h2>Done</h2></summary>…</details>`.
2. CSS: `summary.band-head::after { content:none }`; draw the chevron on `summary.band-head > h2::after` with the same style as `summary::after`, turned by `details[open] > summary.band-head > h2::after`. Replace `.band:first-child > h2` with `.band:first-child > summary > h2` and `.band > h2 + .group > summary` with `.band > summary + .group > summary`. Keep h2 size, margins, border.

## Task 3: one test in `app.test.js`

Table-driven, as in the spec § Tests: renderStatus open/collapsed band (sub-sections unaffected), renderChief with and without `bandKey('pm')`, and every band key starts with `band:` and matches no group name.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
