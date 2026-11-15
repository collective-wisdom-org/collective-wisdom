# CW-334 plan: Linear and Jira links on the dashboard

Spec: `docs/superpowers/specs/2026-11-14-cw-334-dashboard-tracker-links-design.md`. Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` (Node 24+) and `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: reader and buildApi (`agent-team/scripts/dashboard/api.ts`)

- Export `type TrackerLinks = { issue(id: string): string | undefined; backlog: string | null }` and `trackerLinksFromProject(markdown): TrackerLinks | null`, next to `repoUrlFromProject()`. Add a row reader like `trackerIsGithub()` that returns the value cell for a row name (exact or `Name (` prefix).
- Per the spec design item 1: github needs the Repo link; jira needs `Jira site` (https, no TODO/`<`, not `example.atlassian.net`, trailing `/` dropped) and `Jira project key` (`^[A-Z][A-Z0-9_]+$`); linear needs a `https://linear.app/<workspace>/...` link in the `Linear team name` row (workspace `^[A-Za-z0-9-]+$`), team key from `/team/<KEY>/` else the `Issue identifier prefix` row. Issue links only for ids `<KEY>-N` with that tracker's own key (github: any id ending `-N`, as today). Jira backlog: `<site>/issues/?jql=` + `encodeURIComponent('project = KEY AND statusCategory = "To Do" ORDER BY created DESC')`.
- `buildApi` gets optional input `links?: TrackerLinks | null`. Replace the two `issueUrl` sites and the `moreUrl` with `links`. When `links` is `undefined`, derive GitHub links from `repo` so existing tests pass unchanged. When `null`, no links.

## Task 2: merged and server

- `merged.ts`: `MergedConfig` gets optional `issueUrl?: (id: string) => string | undefined`. In `parseMerged`, when present use it for `entry.issueUrl`; else keep the `issueUrls` GitHub behavior.
- `server.ts`: call `trackerLinksFromProject(text)` in `api()`; pass `links` to `buildApi`; set `mergedCfg.issueUrl = links?.issue` (keep `issueUrls`). Keep the `fromFile` logic.

## Task 3: tests (table-driven, keep short)

- `api.test.ts`: one table over `trackerLinksFromProject` (github, jira, linear; filled, rows missing, TODO, example site, template placeholder link) checking `issue('<KEY>-7')`, another prefix, and `backlog`; one `buildApi` case with Jira `links` checking a status row `issueUrl`, a Backlog row `issueUrl` and the group `moreUrl`.
- `merged.test.ts`: one case with a Linear `issueUrl` function.
