# CW-334: Link dashboard tickets and the full backlog for Linear and Jira

**Status:** Draft
**Ticket:** [#334](https://github.com/collective-wisdom-org/collective-wisdom/issues/334)

## Goal

On a Linear or Jira repo, a dashboard card's ticket id opens the ticket in that tracker, and the Backlog group's "Full backlog" link opens the tracker's backlog. GitHub repos behave exactly as today.

## Today

Facts from `main` at `0d708cc`.

- `repoUrlFromProject()` in `agent-team/scripts/dashboard/api.ts:57` returns `{ url, isGithubIssues }` from the `Repo` row's `<https://...>` link, or `null` with no link.
- `buildApi` sets `issueUrl` on in-flight status rows (`api.ts:224`) and on Todo and Backlog rows (`api.ts:264`), and `moreUrl` on the Backlog group (`api.ts:269`), only when `repo.isGithubIssues`.
- `parseMerged()` in `merged.ts:37` sets the Done row `issueUrl` to `https://github.com/<slug>/issues/N` when `MergedConfig.issueUrls` is true. `server.ts:344` sets that from `repo.isGithubIssues`.
- `page/app.js` draws `issueUrl` and `moreUrl` only when they are http(s). It needs no change.
- Jira: `trackers/jira.md` has a `Jira site` row (example `https://example.atlassian.net`) and a `Jira project key` row, and defines `ticket-url` as `<Jira site>/browse/KEY`. `setup_repo.py` writes both as `TODO(<owner>)` for the user to fill.
- Linear: the template's `Linear team name` row reads `<team name> (key `<PREFIX>`, <https://linear.app/<workspace>/team/<PREFIX>/overview>)`. But `setup_repo.py:416` rewrites the whole row as `` `<scope>` `` (`test_setup_repo.py:177` expects `` | Linear team name (Linear only) | `Acme` | ``), so a repo set up by the script has no Linear link. No row records the workspace.

## Design

1. **New reader `trackerLinksFromProject(markdown)`** in `api.ts`, beside `repoUrlFromProject()`. It returns `{ issue(id): string | undefined, backlog: string | null }` for the tracker named in the `Tracker` row, or `null` when it can't build any link. It reads `project.md` rows the same way `trackerIsGithub()` does.
   - **GitHub:** needs the `Repo` link. `issue` gives `<repo>/issues/N` for an id ending `-N`; `backlog` is `<repo>/issues`. Same as today.
   - **Jira:** needs `Jira site` and `Jira project key`; the `Repo` link is not needed. The site is the row's first backticked value or `<...>` link. It must parse as an `https:` URL, with no `TODO`, no `<` placeholder and not the `example.atlassian.net` host; a trailing `/` is dropped. The key must look like a Jira key (`^[A-Z][A-Z0-9_]+$`).
     - `issue(id)` gives `<site>/browse/<id>` only for an id of the form `<KEY>-N`.
     - `backlog` is `<site>/issues/?jql=` plus the encoded `project = <KEY> AND statusCategory = "To Do" ORDER BY created DESC`.
   - **Linear:** needs a `https://linear.app/<workspace>/...` link inside the `Linear team name` row; the `Repo` link is not needed. The workspace must match `^[A-Za-z0-9-]+$`. The team key is the `/team/<KEY>/` segment of that link, else the `Issue identifier prefix` row.
     - `issue(id)` gives `https://linear.app/<workspace>/issue/<id>` only for an id of the form `<KEY>-N`.
     - `backlog` is `https://linear.app/<workspace>/team/<KEY>/backlog`.
   - Anything missing, a `TODO`, or a placeholder gives no link for that part, as today.
2. **`buildApi`** takes an optional `links` input. Both `issueUrl` sites use `links.issue(id)`, and the Backlog group's `moreUrl` uses `links.backlog`. When `links` is not passed, it falls back to the GitHub links from `repo` as today, so the existing tests keep passing unchanged.
3. **`merged.ts`**: `MergedConfig` gets an optional `issueUrl(id)` function. When present, `parseMerged()` uses it for the Done row `issueUrl`. `issueUrls: true` without it keeps today's GitHub link.
4. **`server.ts`** reads `trackerLinksFromProject(text)` beside `repoUrlFromProject(text)`, passes it to `buildApi` as `links`, and puts its `issue` on `mergedCfg`. Merged PRs still need the `Repo` link, since they are read from GitHub.
5. **Tests**, table-driven:
   - `api.test.ts`: one table over `trackerLinksFromProject` for github, jira and linear, filled and with rows missing, `TODO`, the example site, and the template placeholder link. Each case checks `issue('<PREFIX>-7')`, an id with another prefix, and `backlog`. One `buildApi` case with Jira `links` checks a status row's `issueUrl`, a Backlog row's `issueUrl` and the group's `moreUrl`.
   - `merged.test.ts`: one case where `issueUrl` is a Linear function sets the Done row link.

## Leaves out

- Any change to `setup_repo.py` or `agent-team/templates/project.md` (see the first call below).
- Showing Linear or Jira Todo and Backlog lists differently: `lists.ts` already reads them from the Chief of Staff's file.
- Calling the Linear or Jira APIs from the dashboard.
- `page/app.js` and the card (CW-266, CW-332).
- A live check of the Linear and Jira URL shapes. They follow the products' usual paths and need a browser check before merge.

## Calls I made

- **No setup change, so Linear links only appear after a hand edit.** `setup_repo.py` rewrites the `Linear team name` row to the bare team name, so a script-set-up Linear repo has no workspace link and gets no Linear links. Fixing that means a new setup answer (the workspace) and an interview question in `chief-of-staff/setup.md`, which is beyond this ticket. The PR will say so and suggest a follow-up ticket for a `Linear workspace URL` row filled at setup, which I think is the better fix. Until then a Linear user adds the link to the row by hand, in the template's shape.
- **Jira backlog link shows every "To Do" category ticket**, so it includes Todo as well as Backlog. Jira has no fixed "backlog" URL outside boards, and the board id isn't recorded. Sorted newest first.
- **Jira site must be `https:`.** A plain `http:` site gives no link.
- **Linear team key comes from the link first**, then the `Issue identifier prefix` row. In Linear they are the same key.
- **Jira and Linear ticket links need the ticket's own prefix.** An id with another prefix gets no link, so a stray id can't make a wrong link.
- **`buildApi` keeps a GitHub fallback** when `links` is not passed, so the GitHub tests don't change.
