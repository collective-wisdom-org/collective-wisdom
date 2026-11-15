# CW-266 plan: a friendly dashboard

Spec: `docs/superpowers/specs/2026-11-14-cw-266-friendly-dashboard-design.md`. Only the three page files under `agent-team/scripts/dashboard/page/` change. Prior build to port by hand: `pr/267`.

## Task 1: helpers and tests (`app.js`, `app.test.js`)

- Add `groupLabel`, `stageSentence` (with ` since HH:MM`), `riskText`, `dayWords`, `actionFor`, `ganttSummary`, exported where the spec says.
- One table-driven test per rule in spec section 8.

## Task 2: render functions

- `renderStatus` and the ticket card/row, `renderBadges` header sentence, `renderMerged` (Done rows), `renderChief`, per spec sections 2 to 5.
- Keep every browser-shell hook from the spec's Constraints. The shell code stays as is.

## Task 3: `index.html`

- Tokens (spec section 7), segmented tabs, card and row styles, gantt styling, band and group headings, error banner, 360px fit, multi-column grid when wide, chevron in CSS.

## Task 4: verification

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`
- `python3 -I -m pytest -q agent-team/scripts` (or `uvx pytest -q agent-team/scripts`)
- One-off contrast script outside the repo: every text/background pair in `index.html`, light and dark, at least 4.5:1.
- Headless Chrome against a stub `/api` snapshot at 360px and 1280px, light and dark; `scrollWidth <= clientWidth` at 360px; look at the screenshots.
