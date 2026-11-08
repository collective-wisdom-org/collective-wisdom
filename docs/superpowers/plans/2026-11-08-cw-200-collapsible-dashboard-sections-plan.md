# CW-200 plan: collapsible dashboard sections

Spec: `docs/superpowers/specs/2026-11-08-cw-200-collapsible-dashboard-sections-design.md`

## Task 1: markup and test

- `agent-team/scripts/dashboard/page/app.js`: `renderStatus(groups, open = new Set(), collapsed = new Set())` draws `<details class="group" data-group="…"[ open]><summary><h3>name <span class="pill">n</span></h3></summary><ul class="cards">…</ul></details>`. `open` unless the name is in `collapsed`.
- `page/app.test.js`: one table-driven test (all open by default, named section closed, heading and pill kept, `data-group` escaped).
- Check: `node --test agent-team/scripts/dashboard/page/app.test.js`

## Task 2: browser shell and styles

- `app.js` browser block: read and write the collapsed names in `localStorage` key `cw-dashboard-collapsed` (JSON array, try/catch around every access). A capture-phase `toggle` listener on `document` for `details.group` adds or removes the name. `poll()` passes the stored set as `collapsed`.
- `index.html`: `summary` cursor pointer; `details.group > summary > h3` inline; keep `#status > .group:first-child h3` margin rule working.

## Task 3: docs

- `README.md` dashboard paragraph: each stage section collapses from its heading and the page remembers it in the browser.
- Check: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` and `python3 -I -m pytest -q agent-team/scripts`.
