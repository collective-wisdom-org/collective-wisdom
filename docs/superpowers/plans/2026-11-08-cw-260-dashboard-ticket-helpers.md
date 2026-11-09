# CW-260 plan: ticket helpers on the Chief of Staff tab

Spec: `docs/superpowers/specs/2026-11-08-cw-260-dashboard-ticket-helpers-design.md`

1. `api.ts`: `TeamRole` gains `'helper'`; `HEADINGS` gains `'TICKET HELPER'`. In `buildApi`, split the merged team rows by role: `pm` keeps `ranking`/`hygiene`, new `helpers` key holds `helper` rows. `Api` type gets `helpers`.
2. `history.ts`: `ROLES` gains `helper`; `build` caps helper entries at 50 apart from project manager entries (50) and ticket sessions (500).
3. `page/app.js`: `ROLE_LABELS` gains `helper`; `renderChief(api, page, open, size, helperPage)` renders a `Ticket helpers` list after the project manager list with its own pager (`data-helper-page`), `data-helper` on its details and chart bodies, and the empty message; returns `{ html, page, helperPage }`. `drawCharts` draws `.chart-body[data-helper]` from `data.helpers`. The page script keeps `helperPage`, handles its pager click, and keeps `data-helper` details open across polls.
4. Tests: per spec § Tests.
