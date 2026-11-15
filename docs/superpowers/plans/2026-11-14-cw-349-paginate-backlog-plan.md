# CW-349 plan: paginate the dashboard Backlog

Spec: `../specs/2026-11-14-cw-349-paginate-backlog-design.md`. Files: `agent-team/scripts/dashboard/api.ts`, `api.test.ts`, `page/app.js`, `page/app.test.js`, `page/index.html` (only if spacing needs a rule).

## Task 1: API sends every Backlog row
- `api.ts`: remove `BACKLOG_SHOWN` and the slice; Backlog `rows` is the whole sorted list. Keep `count`, `moreUrl`, order.
- `api.test.ts`: turn the "top 3" test (around line 457) into "sends every row by priority then newest, counts them all, links to the issues page", with more than 10 items.

## Task 2: page helper and pager
- `app.js`: export `pageOf(length, page, size)` -> `{ at, pages }` (`pages = max(1, ceil(length/size))`, `at = min(max(0, trunc(page)||0), pages-1)`). Use it in `renderMerged` and `teamList` (output unchanged).
- `renderStatus(groups, open, collapsed, info, backlogPage = 0)`: for group `Backlog` draw rows `at*10..(at+1)*10`; when `pages > 1` add `<nav class="pager">` (Previous, `Page X of Y`, Next; `data-backlog-page`; disabled at the ends) after the list and before the `Full backlog` link. Pill keeps `g.count`.
- Page script: `let backlogPage = 0`; click on `button[data-backlog-page]` sets it and redraws `#status` from `last` (keep open charts/Details/collapsed, as the poll does); poll passes `backlogPage`; after each draw set `backlogPage` to the clamped `at`. The `shownStatus` change check must also include `backlogPage` so a page change redraws.
- `app.test.js`: one table-driven test over `renderStatus` (Backlog 0/10/11/25 rows x pages -1,0,1,2,9,NaN): ids drawn in order, nav shown or not, `Page X of Y`, disabled button, pill full count.

## Verify
`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
