# WISE-482: Show epic and blocked icons on dashboard cards and stop drawing epics as cards

**Status:** Draft
**Ticket:** [#482](https://github.com/collective-wisdom-org/collective-wisdom/issues/482)

## Goal

Epics stop taking up cards on the dashboard. A ticket's card says which epic it belongs to and whether another ticket blocks it, with small icons stacked under the owner avatar at the right of the card.

## Today

- `agent-team/scripts/dashboard/backlog.ts` reads `gh issue list --json number,title,labels,author,createdAt` once a minute and lists open team-authored issues as Backlog (no `status:` label) or Todo (a lone `status:todo`). An epic is listed like any ticket.
- `api.ts` (`buildApi`) turns that list into the Todo rows of the spec queue group and the `Backlog` group, and builds the Ship loop rows from `state.json`. Every row's owner comes from `owner` on the row.
- `page/app.js` draws the owner with `ownerBadge`, placed by `rowHead` in grid column 4, row 1 of `.head` (`page/index.html`, `.owner`).
- The REST issue list (`repos/<slug>/issues?state=open`) carries `sub_issues_summary.total` and `issue_dependencies_summary.blocked_by` on each issue, but not `parent_issue_url` (checked: the key is missing from list items and present on a single-issue read). `blocked_by` counts open blockers only: #443 has `blocked_by: 0`, `total_blocked_by: 1`, its one blocker closed.
- `issues/E/sub_issues` lists an epic's children; `issues/N/dependencies/blocked_by` lists a ticket's blockers with `number`, `title`, `state` and `repository_url`.
- The `blocked` stage and the card's `blocked` class mean the Chief of Staff needs an answer from the user. This ticket does not touch them.

## Change

### 1. Relations read (`backlog.ts`)

After each good `gh issue list` read, `read` runs a second read, the relations, through the same `run` helper:

1. `api repos/<slug>/issues?state=open&per_page=100 --paginate` with a `--jq` that keeps, for each item that is not a pull request, `number`, `title`, `sub_issues_summary.total` and `issue_dependencies_summary.blocked_by`.
2. For each issue with `total > 0` (an epic): `api repos/<slug>/issues/<E>/sub_issues --paginate --jq '[.[].number]'`. Each child number maps to that epic's id and title.
3. For each issue with `blocked_by > 0`: `api repos/<slug>/issues/<N>/dependencies/blocked_by --jq ...`, keeping blockers whose `state` is `open`. A blocker in this repo is named by `idForNumber`; one in another repo by `<owner>/<repo>#<number>` from its `repository_url`. Titles are cleaned like the list titles (control characters out, 200 characters).

The result is a map from ticket id to `{ epic?: { id, title }, blockedBy: { id, title }[] }` for every open issue in the repo, plus the set of epic numbers. `createBacklog` exposes it as `relations()` (empty without a config, like `get()`).

- **Epic filter.** An issue in the epic set is left out of `get()`, so it is in neither the Todo rows, the `Backlog` group, nor its count.
- **Failure.** If any relations call fails, the read keeps the epic set from the last good relations read (so a known epic stays hidden) and `relations()` returns an empty map until the next good read, so cards draw with no epic and no blocked icon. The list itself still updates, and `error()` is unchanged: a relations failure shows no error line.
- The relations read runs only on GitHub. On Linear or Jira (lists from the saved file) `relations()` is empty and nothing changes.

### 2. Rows carry the relations (`api.ts`, `server.ts`)

`buildApi` takes `relations` (default `{}`). Each Ship loop row and each Todo and Backlog row whose id is in the map gets `epic` (when it has one) and `blockedBy` (an array, empty when not blocked). A row with no entry (a ticket helper, a closed issue, a non-GitHub tracker, a failed read) gets neither field. Done tab rows get neither: their issues are closed. `server.ts` passes `backlog.relations()` on GitHub and `{}` when the lists come from the file.

### 3. Icons on the card (`page/app.js`, `page/index.html`)

`rowHead` puts a new `marks` column at the right end of the card in place of the bare owner badge: a flex column spanning the id and title rows of `.head`, top to bottom:

1. the owner avatar (`ownerBadge`, unchanged; an empty slot when there is no owner),
2. the epic icon, when the row has `epic`: a small inline SVG, `role="img"`, `title` and `aria-label` `Epic <id>: <title>`,
3. the blocked icon, when the row has `blockedBy`: a red x (`--red`) when the array is not empty, with `title` and `aria-label` `Blocked by:` then one `<id>: <title>` per line; a green check (`--green`) when empty, with `Not blocked`.

Each slot is 20px high. A row with `blockedBy` but no epic keeps the epic slot empty, so the avatar and the blocked icon sit at the same height on every card. A row with neither field draws only the avatar, as today. All text goes through `esc`.

### 4. Tests

- `backlog.test.ts`: one table-driven test for the relations read: an epic left out of `get()`; a child mapped to its epic; open blockers kept and closed ones dropped; a blocker from another repo named by slug; blocker lists fetched only for `blocked_by > 0`; a failed relations call leaving `get()` drawn, `relations()` empty and a known epic still hidden.
- `api.test.ts`: rows get `epic` and `blockedBy` from the map; rows not in it get neither.
- `app.test.js`: one table-driven test for the marks column: epic and red x with their tooltips, green check, no epic (slot kept), no relations (avatar only), and escaped titles.

## Leaves out

- The `blocked` stage styling and its "Needs an answer from you" text.
- Sub-issue progress on an epic.
- How the Chief of Staff and project manager treat epics.
- Icons on Done tab cards and on Linear or Jira repos.

## Calls I made

- **Epic of a ticket comes from the epic's sub-issue list, not `parent_issue_url`.** The REST issue list has no `parent_issue_url`; reading each epic's children costs one call per epic instead of one per ticket.
- **Only open epics count.** A ticket whose epic is closed shows no epic icon, since the read lists open issues only.
- **A relations failure is silent.** The cards draw without icons and no error line shows; the list's own error line stays for list failures only. A known epic stays hidden through a failed read, so a blip does not bring epic cards back.
- **The epic slot is kept empty on a card with no epic**, so the blocked icon does not move between cards ("do not shift" in the ticket).
- **Icons appear on Ship loop and Backlog-tab cards only**, not on the Done tab (closed issues) or for ticket helpers (no issue).
- **A blocker in another repo** is named `<owner>/<repo>#<number>`.
- **The relations read reads every open issue** with `--paginate`, not the 200 cap of the list read, so Ship loop cards beyond the first 200 still get icons.
- **No new refresh cycle.** The relations read rides on the list read: once a minute and on a new change stamp.
- **Tooltips use the `title` attribute**, like the avatar today, with the same text as the accessible name.
