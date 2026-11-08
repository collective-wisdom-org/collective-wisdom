# CW-187: Replace the dashboard Agents pane with a paginated Merged list

**Status:** Draft
**Ticket:** [#187](https://github.com/collective-wisdom-org/collective-wisdom/issues/187)
**Related:** CW-181 (#184, nested charts), CW-178 (#183), CW-175 (#176, narrow pane), #98 (Gantt history, out of scope)

## Goals

- The dashboard no longer has an Agents section. Charts nested in Status cards stay.
- Where the Agents section was, a `Merged` section lists merged PRs of the repo, newest merge first, ten per page, as cards that look like the Status cards.
- The list comes from GitHub, not `state.json`, so tickets merged more than 24 hours ago still show.
- A `gh` failure keeps the last list on screen and never breaks `/api` or the Status groups.

## Today

Facts from `main` at `2309ea5`.

- `page/index.html` ends with `<h2>Agents</h2>` and `<div id="gantt">`. `page/app.js` `draw()` fills it every second with `renderGantt(last.gantt, now)`.
- `api.ts` `buildApi` returns `{ generatedAt, status, gantt }`. `gantt` holds the snapshots no board card matched (CW-181). Nothing but `app.js` and the tests reads it.
- `api.test.ts` checks snapshot cleaning (end fill, stale, 24-hour cut, worktree-only) by reading `build(...).gantt`, and `server.test.ts` checks the snapshot folder rules (bad JSON, symlinked folder) through `api.gantt`.
- `titles.ts` runs `gh.sh` through `ghRunner(root)` (no shell, 10-second timeout, 1 MB buffer) in the background with a cache, and `/api` never waits on it.
- `gh.sh pr list --state merged --json number,title,headRefName,mergedAt,url` returns PRs in an order that is not merge order (today #180 merged after #184 but is listed after it).
- Merged PR titles end with the ticket id (`feat: ... (CW-181)`), and branches follow `feat/cw-N-...`.
- `README.md` § Local dashboard says worktree sessions with no card "stay in an Agents list".

## Builds

### 1. Merged PR reader (`merged.ts`, new)

- `createMerged({ run, now })`, the same shape as `createTitles`. `want(cfg)` starts a background read when none is running and the last read started 60 seconds or more ago; `get()` returns the last good list; `idle()` waits for a running read (tests).
- `cfg` is `{ prefix, slug }`, the same `TitleConfig` `server.ts` already builds, except that the merged list needs only a GitHub repo, not GitHub issues: the slug comes from the `Repo` row's GitHub URL whatever the tracker.
- The read runs `pr list --repo <slug> --state merged --limit 200 --json number,title,headRefName,mergedAt,url`.
- A pure `parseMerged(json, cfg, repo)` turns the output into entries:
  - The ticket id comes from the branch (`feat/<prefix lower>-N-` or `feat/<prefix lower>-N`), else from a `(<PREFIX>-N)` at the end of the title. A PR with neither (release tooling, hand PRs) is left out.
  - `title` is the PR title with the trailing `(<PREFIX>-N)` removed, cleaned like tracker titles (control characters to spaces, trimmed, 200 characters at most).
  - `mergedAt` is the parsed time in milliseconds; an entry whose time does not parse is left out.
  - `prUrl` is the PR `url` only when it starts with `https://github.com/<slug>/pull/`; else it is built from `number`. `issueUrl` is set only when the tracker is GitHub issues, as for Status cards.
  - Entries are sorted by `mergedAt`, newest first, with PR number as the tie-break.
- Output that is not JSON, not an array, or a `gh` error keeps the last good list and is retried after 60 seconds.

### 2. API (`api.ts`, `server.ts`)

- `Api` drops `gantt` and gains `merged: { id, title, prUrl, issueUrl?, mergedAt }[]`. `buildApi` takes `merged` as an input and passes it through.
- Unmatched snapshots are dropped, since nothing shows them now. Cleaning and matching stay as they are.
- `server.ts` calls `merged.want(cfg)` on each `/api` call, next to `trackerTitles.want`, and passes `merged.get()` to `buildApi`.

### 3. Page (`index.html`, `app.js`)

- `index.html`: `<h2>Agents</h2>` and `#gantt` become `<h2>Merged</h2>` and `<div id="merged">`.
- `renderMerged(list, page, size = 10)` is pure and returns `{ html, page }`, with `page` clamped to the last page. It draws one `ul.cards` of `li.ticket` cards, each with the id linked to the issue, a `PR` link, the title, and a `merged` line with the local merge time (`YYYY-MM-DD HH:MM`). No stage or risk badge, `next` line, copy button or chart. An empty list shows the quiet line `Nothing merged yet`.
- Below the cards, when there is more than one page: a `nav.pager` with `Newer` and `Older` buttons (disabled at either end) and `Page 2 of 5` between them. The buttons wrap in a narrow pane, like the card header.
- `poll` redraws `#merged` only when the list changed or the page changed. The current page lives in a page variable, so a poll keeps it; it is clamped when the list gets shorter. The click handler that already serves the copy buttons also handles `button[data-page]`.
- `draw()` stops touching `#gantt`. `renderGantt` stays for the nested charts.

### 4. Tests

- `merged.test.ts`, one table-driven test of `parseMerged`: newest first across out-of-order input; id from branch; id from title; PR with no id left out; bad `mergedAt` left out; a foreign `url` replaced by the built one; `issueUrl` only for GitHub issues.
- `merged.test.ts`, one test of the reader: a good read, then a failing read keeps the list, then no new read before 60 seconds and one after.
- `app.test.js`, one table test of `renderMerged` paging: 25 entries give pages of 10, 10, 5; page past the end clamps; the first page disables `Newer`, the last disables `Older`; one page has no pager; escaping of the title.
- `api.test.ts` and `server.test.ts`: the checks that read `api.gantt` move to a row that matches, or check that `gantt` is gone and that a matched row still gets its charts. No new cases.
- `server.test.ts`: its temp repos have no `project.md`, so no `gh` call runs; add an assertion that `/api` answers with `merged: []`. The `gh` failure path itself is covered in `merged.test.ts`.
- The AGENTS.md dashboard test command passes.

### 5. Docs

- `README.md` § Local dashboard: replace "worktree sessions with no card stay in an Agents list" with a sentence on the Merged list.

## Leaves out

- Changes to the per-card Gantt charts.
- Closed but unmerged PRs and canceled tickets.
- A Gantt history mode (#98).
- Merged PRs older than the newest 200.
- Showing worktree sessions that match no card anywhere.

## Calls I made

- **Sessions that match no Status card are no longer shown anywhere.** Today they sit in the Agents list (the Chief of Staff, the root checkout, a worktree of a ticket off the board). The ticket deletes that list and the `gantt` array, so they drop out. Keeping them would need a new home the ticket doesn't ask for.
- **PRs with no ticket id are left out** (no `feat/cw-N` branch and no `(CW-N)` title suffix). The list is of merged tickets, and a card needs an id.
- **The newest 200 merged PRs only** (20 pages of 10). One `gh` call, no server-side paging.
- **Paging is in the page, not the server.** The server sends the whole cached list in `/api`; the page slices it. 200 short entries is a few tens of kilobytes every 5 seconds on localhost.
- **Page size 10**, buttons `Newer` and `Older` with `Page N of M`.
- **The list is read from GitHub at most once a minute**, and only while the page polls `/api`. A merge shows up within about a minute.
- **A new merge shifts every page by one entry.** The page number holds through a poll, but its contents move. Pinning contents would need a cursor, which isn't worth it here.
- **The title is the PR title minus its `(CW-N)` suffix**, not the issue title, so no extra `gh` call per entry. The `feat:` prefix stays.
- **Merge time shows as local `YYYY-MM-DD HH:MM`**, not "3 hours ago", so it doesn't need redrawing every second.
- **The merged list needs only a GitHub repo.** In an app whose tracker is Linear or Jira, the cards show the id as text with no issue link, like Status cards there.

## Touches

None of these (no data, money, auth, user email or migrations). The dashboard server makes one more read-only `gh` call a minute.
