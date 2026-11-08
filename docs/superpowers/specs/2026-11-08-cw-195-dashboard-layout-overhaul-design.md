# CW-195: Overhaul the dashboard layout so it is easy to read

**Status:** Shipped
**Ticket:** [#195](https://github.com/collective-wisdom-org/collective-wisdom/issues/195)
**Shipped:** in PR #203, with differences: [as-built](../as-built/2026-11-08-cw-195-dashboard-layout-overhaul-as-built.md)
**Related:** #198 (sort by last updated, merged in #201), #200

## Goal

Open the dashboard and see in a few seconds what needs you. Tickets waiting on your approval come first and look different; work in progress reads normally; queued and merged items are quiet. The page shows the same data as today, in less space and with less noise.

## Today

Facts from `main` at `3ab6621`.

- `page/index.html` holds all CSS in one `<style>` block. `page/app.js` has the pure renderers `renderStatus`, `renderBadges`, `renderMerged`, `renderGantt` and the browser shell (5 second poll, 1 second Gantt redraw, copy button, pager).
- `/api` gives `status: { name, count, rows }[]` in the order of `groupTickets`: Awaiting merge approval, Awaiting teammate review, Merging, Queued to merge, Speccing, Awaiting build approval, Building, Queued to build, Other. `Other` holds `spec-queued` and `blocked` rows. Since #201, non-queued rows in each group come newest update first.
- Every card is the same gray box. Its top row holds id, stage badge, risk badge, PR link and "Copy thread link". The stage badge repeats the group heading in every group but `Other`.
- The Gantt has a nine-column table on containers 48rem and wider, and a stacked layout below.
- `server.ts` sends `default-src 'self'; style-src 'self' 'unsafe-inline'` for `/`. Gantt bars use inline `style` attributes, which that allows.

## Builds

All changes are in `agent-team/scripts/dashboard/page/` (`index.html`, `app.js`, `app.test.js`). No change to `api.ts`, `merged.ts`, `server.ts` or the status groups.

1. **Three bands, in this order.** `renderStatus` sorts the groups it gets into bands, keeping the `/api` order inside each band:
   - **Needs you:** Awaiting merge approval, Awaiting build approval.
   - **In progress:** Awaiting teammate review, Merging, Speccing, Building, and any group name the page does not know.
   - **Queued:** Queued to merge, Queued to build, Other.
   Each band has a small heading ("Needs you", "In progress", "Queued"); a band with no groups is not drawn. Group headings stay (name and count pill) inside their band.
2. **Needs-you cards stand out.** Cards in the two approval groups get a colored left edge and a tinted background: the merge group uses the same red family as the merge header badge, the build group the same amber as the build header badge. Their count pills use the same colors. In `Other`, a `blocked` card gets the red edge too, since it waits on an answer.
3. **Card layout.**
   - Line 1: id link (bold, never wraps or truncates) followed by the title, which wraps under itself. With no title, the id stands alone.
   - Line 2, smaller and muted: risk badge, `PR` link, then the copy button at the right end. The button keeps its `data-copy` and text "Copy thread link".
   - Line 3, muted: the `next` text.
   - The "Agents" disclosure stays last with its count pill, styled as a quiet text toggle.
   - The stage badge is dropped in every group except `Other`, where it is the only place `spec-queued` and `blocked` differ. Shown there as plain words ("blocked", "spec queued"), not the raw slug.
4. **Queued and merged rows are compact.** Rows in the Queued band and in Merged render as a flat list, not boxed cards: one line of id and title, with risk, PR, copy button and `next` (for Merged, "merged 2026-01-02 03:04") on a muted second line. No background fill; a thin divider between rows. The cards grid stays for Needs you and In progress.
5. **Gantt reads at a glance.** One layout at every width, no column header row:
   - Line 1: agent name (indented by depth), the timeline track, cost on the right.
   - Line 2, muted and smaller, under the name: repo · start to end (`12:01 to 12:20`, or `12:01, running`) · tokens · model · harness. Empty parts are skipped.
   - At container widths of 36rem and up, the name and meta sit in a fixed 14rem column left of the track; below that the track drops under them, full width.
   - The session heading shows the cwd in a smaller monospace line with the total cost; the stale pill and the stale fade stay. Running bars keep the amber color, done bars green.
   - No data leaves: name, repo, start, end, tokens, cost, model, harness and every segment stay.
6. **Header, states and controls.**
   - Header: the title and the badges on one row when they fit, badges wrapping under it in a side pane. The merge badge first, then build, then the build queue (as today); the queue badge is quiet (outline only).
   - Buttons (copy, pager) share one style: outline, the same height, a visible focus ring, a hover state.
   - Error line: a bordered red banner above the status, hidden when empty, still `role="status"`.
   - Empty states keep their text ("No state yet", "No sessions yet", "Nothing merged yet") in a muted line.
   - Spacing on a 4px scale; type sizes limited to four: page title, band heading, body, small.
7. **Colors.** All text and badge pairs meet WCAG AA (4.5:1 for body and small text) in light and dark. Muted text is checked against both the page and card backgrounds. The build checks every pair with a one-off script and reports the ratios in the PR; no test file for it.
8. **Shell behavior stays.** The 5 second poll still keeps open `<details>`, a text selection, the copy button label and the Merged page. Status html is still rebuilt only when the status JSON (with Gantt sessions by id) changes. No new network requests, no external fonts or images, no new inline scripts.
9. **Tests.** `app.test.js` changes only where markup changed on purpose: the Gantt header row and model/harness cells test, the merged card class, and one new table-driven test for the bands (order across bands, `/api` order inside a band, unknown group name to In progress, empty band not drawn, stage badge only in `Other`).
10. **Screenshots.** Before and after, with the same data, at a 360px side-pane width and a 1280px width, light and dark: eight images in the PR. Taken with headless Chrome from a fixed `/api` JSON snapshot served next to each version of the page by a throwaway local script outside the repo. The snapshot is captured once from the live dashboard so the data is real.

## Leaves out

- New data, API fields, panes or header badges (for example a blocked count).
- Changing the group order in `/api` or `groupTickets`; the bands are a page-side order.
- A framework, build step, new dependency, web font or icons.
- The status-pane mod and the agent-gantt mod.
- A theme toggle; dark mode still follows `prefers-color-scheme`.

## Calls I made

- **The page reorders groups into bands.** "Awaiting build approval" is sixth in the `/api` order, under work that doesn't need you. The ticket asks for what needs you first and keeps `/api` out of scope, so the page sorts groups into Needs you, In progress and Queued. A group name the page doesn't know goes to In progress, so a new group never disappears.
- **Awaiting teammate review is In progress, not Needs you.** It waits on a teammate, not the approver.
- **Blocked cards get the red edge, but stay in `Other`.** Splitting `Other` would change the groups; marking the card shows it needs an answer without that.
- **The stage badge stays in `Other` only**, in plain words, because there the heading doesn't say the stage. Everywhere else it repeated the heading and is dropped as noise.
- **The nine-column Gantt table goes.** Its header row and seven narrow columns made each row a scan across the page. The same values move to one muted line under the agent name; start and end merge into one range. This is the main "data looks different" change; nothing is dropped.
- **Queued and Merged become compact lists.** They're routine, so they lose the card box. Merged keeps 10 per page and the pager.
- **Colors stay GitHub-like and tied to the header badges**: red family for merge approval and blocked, amber for build approval, so a badge and the cards it counts match.
- **Breakpoints:** 36rem container width for the Gantt two-column row (a side pane is narrower), the existing 22rem minimum card width for the grid.
- **Screenshot widths** 360px and 1280px, captured with headless Chrome from one fixed snapshot so before and after show the same data.

## Touches

None of these: data, money, auth, user email, migrations.
