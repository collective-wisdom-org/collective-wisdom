# CW-296: Show the 3 top Backlog tickets on the Ship loop tab with a link to the full backlog

**Status:** Shipped
**Ticket:** [#296](https://github.com/collective-wisdom-org/collective-wisdom/issues/296)
**Shipped:** in PR #297, as specified

## Goal

The Backlog section of the Ship loop tab lists every open Backlog ticket, which buries the rest of the page as the Backlog grows. Show only the 3 highest priority ones, newest first within a priority, keep the full count on the heading, and link to the tracker's full backlog under them.

## Today

- `agent-team/scripts/dashboard/backlog.ts` `createBacklog` runs `gh issue list --limit 200 --json number,title,labels,author` once a minute, keeps team authors only, and returns `{ id, title, state }` for Todo and Backlog in the tracker's order (newest first). It reads no priority and no `createdAt`.
- `agent-team/scripts/dashboard/api.ts` `buildApi` turns each of `Todo` and `Backlog` into a status group `{ name, count, rows }` with every row, skipping tickets already in state or in the merged list.
- `page/app.js` `renderStatus` draws both groups as flat rows in the `Not started` band. A group has no place for a link.
- On GitHub, priority is one of the labels `priority:urgent`, `priority:high`, `priority:medium`, `priority:low`; no `priority:` label means no priority (`trackers/github.md`).

## Design

### 1. `backlog.ts` reads priority and creation time

- The `issue list` call asks for `number,title,labels,author,createdAt`.
- `BacklogItem` gains `priority: 'urgent' | 'high' | 'medium' | 'low' | null` and `createdAt: number | null` (milliseconds; null when the field is missing or does not parse as a date).
- `priority` comes from the issue's `priority:` labels. Unknown `priority:` values are ignored. If an issue has more than one known `priority:` label, the highest wins.
- Everything else (team author check, status rule, title cleaning, keeping the last good list) stays as it is.

### 2. `api.ts` keeps the top 3 and adds the link

- The Todo group is unchanged: every row, tracker order.
- The Backlog group's `count` stays the number of Backlog tickets it would list today (open, team author, not in state or merged), so the heading pill shows how many there are in all.
- Its `rows` are those tickets sorted by priority (urgent, high, medium, low, none), then by `createdAt` newest first, with a missing `createdAt` last within its priority, then tracker order for any tie. The first 3 are kept.
- A status group may carry `moreUrl`. The Backlog group gets `moreUrl: <Repo url>/issues` when the repo is known and its tracker is `github` (`repo.isGithubIssues`, from the same `Repo` row `repoUrlFromProject` reads). Other groups never get it.
- With no Backlog tickets there is no Backlog group, as today, so no link either.

### 3. `page/app.js` draws the link

- A group with an `http(s)` `moreUrl` gets one line after its rows: a link `Full backlog`, opened like the other issue links. A `moreUrl` that is not `http(s)` draws nothing. The URL is escaped like every other field.
- The link sits inside the group's collapsible section, so it hides with the rows.

### 4. README

README.md § Local dashboard: the Not started band sentence says Todo lists every Todo ticket in the tracker's order, Backlog shows the 3 highest priority tickets (newest first within a priority) with the full count on its heading, and a `Full backlog` link to the repo's issues page.

## Leaves out

- Linear and Jira Backlog sections and board links; the dashboard reads no Linear or Jira tickets today.
- Any change to the order the Chief of Staff or the Backlog ranking child starts tickets in.
- Making the ticket helper file a priority.
- Reading more than the 200 newest open issues.
- Limiting or reordering the Todo group.

## Calls I made (surprising first)

- **The link goes to `<Repo url>/issues`, the plain issues page**, as the ticket says, not a search filtered to Backlog (no `status:` label, which GitHub search can only express by excluding each `status:` label by name). The plain page is stable and needs no label names in the URL.
- **The link text is `Full backlog`.** The ticket names no wording.
- **An issue with two `priority:` labels sorts by the highest one.** The tracker contract says one label, but nothing enforces it.
- **A missing or unparseable `createdAt` sorts last within its priority**, then tracker order breaks any tie, so the list is stable between refreshes.
- **The cut to 3 happens in `buildApi`, not in `backlog.ts`**, because the heading count needs every Backlog ticket after the in-state and merged skips, which only `buildApi` knows.
- **The link is a generic `moreUrl` on the status group** that only the Backlog group sets, rather than a Backlog special case in the page.

## Tests

Per `AGENTS.md` § Testing, one table per rule:

- `backlog.test.ts`: the priority and `createdAt` parse (each priority, none, unknown value, two labels, bad or missing date).
- `api.test.ts`: one table for the Backlog group: mixed priorities and dates give the top 3 in order with no-priority tickets last; a Backlog of 3 or fewer shows all; the count covers every ticket; `moreUrl` is `<Repo url>/issues` for a `github` tracker and absent otherwise; Todo is not cut. A no-priority ticket shows when the Backlog is short covers the helper-filed case.
- `page/app.test.js`: a group with `moreUrl` renders the escaped `Full backlog` link; a non-`http(s)` one renders none.

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` pass. A hand look at the live dashboard goes under the PR's Not proven.

## Touches

None of data, money, auth, user email or migrations. Dashboard display only.
