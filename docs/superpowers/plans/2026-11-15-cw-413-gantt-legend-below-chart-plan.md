# CW-413 plan: Gantt legend below the chart, ticket number above the title

Spec: `docs/superpowers/specs/2026-11-15-cw-413-gantt-legend-below-chart-design.md` (approved). Files: `agent-team/scripts/dashboard/page/app.js`, `page/index.html`, `page/app.test.js`, `README.md`.

Test command (from the repo root): `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Task 1: legend

1. `renderGantt`: make `legendHtml` start with `\n` instead of ending with it; emit it after `${oldNote}` inside `<div class="gantt">`; remove it from before the rows.
2. `index.html`: `.legend` margin `var(--s2) 0 0`; the first-row rule becomes `.grow:first-child { border-top:0; }`.
3. `app.test.js` (~line 720): replace the "starts with legend" assertion with one that the `<ul class="legend"` comes after the Total row and is followed only by `\n</div>`. Keep the other assertions.

## Task 2: card top row

CSS only in `index.html`: `.head:has(> .id) { display:grid; grid-template-columns:minmax(0, max-content) auto; justify-content:start; align-items:start; column-gap:var(--s1); }` and `.head .id { grid-column:1 / -1; }`. No test.

## Task 3: README and check

README: "legend above the chart" to "legend below the chart"; top-row sentence says the ticket number sits above the title. Run the test command and `python3 -I -m pytest -q agent-team/scripts`.
