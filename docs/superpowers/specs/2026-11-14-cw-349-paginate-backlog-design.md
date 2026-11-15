# CW-349: Paginate the Backlog section of the dashboard

**Status:** Draft
**Ticket:** [#349](https://github.com/collective-wisdom-org/collective-wisdom/issues/349)

## Goal

The dashboard's Backlog section shows every Backlog ticket, 10 to a page, with previous and next controls, instead of the top 3 and a link to the tracker.

## Today

Facts from `main` at `6e85821`.

- `buildApi` in `agent-team/scripts/dashboard/api.ts` builds the Todo and Backlog groups from the tracker list. Backlog is sorted by priority, then newest first, then tracker order, and `rows` keeps the first `BACKLOG_SHOWN = 3`. `count` is the full number. `moreUrl` is the tracker's backlog URL.
- `renderStatus(groups, open, collapsed, info)` in `dashboard/page/app.js` draws every row it gets and ends a group with a `Full backlog` link when `moreUrl` is http(s).
- The poll in `app.js` runs every 5 seconds and rebuilds `#status` only when the `/api` status JSON changed.
- Merged and the Chief of Staff tab already page their lists: `renderMerged` and `teamList` clamp the page with `Math.min(Math.max(0, Math.trunc(page) || 0), pages - 1)`, draw a `<nav class="pager">` with two buttons and `Page X of Y`, and keep the page in a variable in the page script (`mergedPage`, `pmPage`), so it survives a poll.
- `createBacklog` reads up to 200 open issues.

## Design

1. **API sends every Backlog row.** `buildApi` drops `BACKLOG_SHOWN` and the slice: the Backlog group's `rows` is the whole sorted list, in the same order. `count` and `moreUrl` stay as they are. Agent charts still join Backlog rows as before; more rows can now get one.
2. **One page helper.** `app.js` exports `pageOf(length, page, size)`, returning `{ at, pages }` with `pages = Math.max(1, Math.ceil(length / size))` and `at` clamped as above. `renderStatus` uses it for Backlog. `renderMerged` and `teamList` switch to it too, so the clamping rule lives in one place.
3. **`renderStatus` takes a Backlog page.** A fifth argument, `backlogPage = 0`. For the group named `Backlog`, it draws rows `at * 10` to `(at + 1) * 10`. When `pages > 1`, a `<nav class="pager">` follows the list, before the `Full backlog` link: `Previous`, `Page X of Y`, `Next`, the buttons carrying `data-backlog-page` and `disabled` at the ends, like the Merged pager. With one page or fewer there is no nav. The pill shows `count`, unchanged. Other groups are not paged.
4. **Page state in the script.** A `backlogPage` variable next to `mergedPage`. A click on `button[data-backlog-page]` sets it and redraws `#status` with the cached `last`, keeping open charts, open Details and collapsed sections, as the poll does. The poll passes `backlogPage` to `renderStatus`. After each draw, `backlogPage` takes the clamped `at` (from `pageOf` on the Backlog group's row count), so when the list shrinks the page is the last one, and a later growth does not jump the reader forward.
5. **Styles.** The Backlog pager reuses `.pager`. If it sits badly inside a `details.group`, one rule in `index.html` adds spacing; nothing else changes.
6. **Tests.**
   - `api.test.ts`: the existing "top 3" test becomes "the Backlog group sends every row by priority then newest, counts them all and links to the issues page", with more than 10 items so a slice would fail it.
   - `page/app.test.js`: one table-driven test over `renderStatus` with a Backlog group of 0, 10, 11 and 25 rows and pages -1, 0, 1, 2, 9 and `NaN`: which ids are drawn and in what order, whether the nav shows, the `Page X of Y` text, which button is disabled, and that the pill shows the full count. This covers slicing and clamping. The existing `Full backlog` test stays.

## Leaves out

- Paging Todo or any other section.
- Search, filters or sorting controls.
- Reading more than 200 issues from the tracker.
- Keeping the page across a page reload.
- `mods/agent-gantt`, which has no Backlog.

## Calls I made (surprising first)

- **The page is kept in memory, not in `localStorage`.** The ticket asks that the page survive the 5-second redraw; a variable in the page script does that, like the Merged and Chief of Staff pagers. A reload starts on page 1. The ticket points at `localStorage` only as how collapsed sections persist.
- **Paging happens in the browser, not in `/api`.** `/api` sends all Backlog rows (at most 200) and the page slices them. Merged pages through a `mergedPage` query instead, but there the server trims history; here the list is already in memory and capped, and slicing on the page avoids a poll round trip on each click.
- **Clamping to the last page also happens on a click past the end**, since the same `pageOf` rule handles both. The buttons are disabled at the ends, so this only matters for a shrinking list.
- **`renderMerged` and `teamList` move to the shared `pageOf`.** Same rule, three copies today. Their output does not change.
- **Button words are `Previous` and `Next`**, not Merged's `Newer` and `Older`, since the Backlog is sorted by priority, not time.
- **Page size 10**, as the ticket assumes, and the same as Merged.
- **The pager sits above the `Full backlog` link**, both inside the Backlog section.
