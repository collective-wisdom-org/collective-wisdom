# CW-188 plan: dashboard header and call-to-action badges

Spec: `docs/superpowers/specs/2026-11-08-cw-188-dashboard-header-badges-design.md`

## Task 1: badge function and test (`agent-team/scripts/dashboard/page/`)

- `app.js`: export `renderBadges(groups)` after `renderStatus`. Returns `''` when `groups` is not an array. Looks up `Awaiting merge approval`, `Awaiting build approval`, `Queued to build` by name (missing = 0). Output order: red `badge cta-high` (`X thread(s) awaiting merge approval`, only if X > 0), yellow `badge cta-medium` (`Y thread(s) awaiting build approval`, only if Y > 0), neutral `badge` (`Z ticket(s) in the build queue`, or `No tickets in the build queue`).
- `app.test.js`: one table-driven test: 0, 1, many per badge, missing group, non-array input, singular wording.

## Task 2: markup, styles, poll (`index.html`, `app.js`)

- `index.html`: remove `<h2>Status</h2>`; wrap `<h1>` and `<div id="cta" aria-live="polite">` in a wrapping flex `<header>` (`#cta` has `margin-left:auto`, flex-wrap, gap); `.badge.cta-high` / `.badge.cta-medium` use `--b-high*` / `--b-medium*`; `#error:empty { display:none }` and drop its `min-height`; tighten h1 margin and the first group's `h3` top margin.
- `app.js` `poll()`: inside the `json !== shownStatus` branch also set `#cta` innerHTML from `renderBadges(last.status)`.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
