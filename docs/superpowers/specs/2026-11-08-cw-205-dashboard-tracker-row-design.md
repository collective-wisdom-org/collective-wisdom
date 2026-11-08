# CW-205: Read the tracker from project.md in the dashboard, not the template prose

**Status:** Shipped
**Shipped:** in PR #208, as specified
**Ticket:** [#205](https://github.com/collective-wisdom-org/collective-wisdom/issues/205)
**Related:** #203 and #204 changed the dashboard page; this ticket changes only how `/api` decides that tickets are GitHub issues.

## Goal

The dashboard links tickets to GitHub issues only when the `Tracker` row of `docs/agents/project.md` says `github`. A repo on Linear or Jira gets no issue links, even when its `project.md` still holds the template's "Choosing a tracker" text.

## Today

Facts from `main` at `9ec0086`.

- `repoUrlFromProject` in `agent-team/scripts/dashboard/api.ts` sets `isGithubIssues` with `markdown.includes('Tickets are GitHub issues')`.
- The template (`agent-team/templates/project.md`, line 25) describes the `github` option with that sentence. An app that keeps that section, such as Fathom on Linear, matches the check.
- `server.ts` uses the flag for four things, so all four are wrong for such a repo:
  - the status row `issueUrl` in `buildApi` (`api.ts`),
  - `mergedCfg.issueUrls`, the merged list `issueUrl` (`merged.ts`),
  - `titleCfg`, which turns on GitHub title reads (`titles.ts`),
  - `updated.want(titleCfg)`, the GitHub update-time reads (`updated.ts`).
- `tracker()` in `agent-team/scripts/project_config.py` reads the tracker from a table row whose key is `Tracker` or starts with `Tracker (` (not `Tracker scope`), takes the first backticked token in the Value cell, lowercases it, and reads a missing row or no token as `linear`.

## Builds

1. **`repoUrlFromProject`** sets `isGithubIssues` from the `Tracker` row instead of the prose:
   - A line is a table row when it starts with `|` (after leading spaces). Its cells split on `|` and are trimmed; the first cell is the key, the second the value. The same parse as `_parse` in `project_config.py`.
   - The first row whose key is `Tracker` or starts with `Tracker (` decides. Its value's first backticked token, lowercased, must equal `github`.
   - A missing row, or a row with no backticked token, reads as `linear`: `isGithubIssues` is false.
   - The `url` part and the `null` return when there is no `Repo` link are unchanged.
2. Nothing else changes. `server.ts`, `merged.ts`, `titles.ts` and `updated.ts` already follow the flag, so all four consumers above are fixed by item 1.
3. **Test.** One table-driven test in `api.test.ts` for `repoUrlFromProject`, with a `Repo` row in every case:
   - a `github` row gives `true`,
   - a `linear` row gives `false`,
   - no `Tracker` row gives `false`,
   - a `linear` row in a file that also contains "Tickets are GitHub issues" gives `false`.
   The existing check that this repo's own `project.md` gives `isGithubIssues: true` stays.

## Leaves out

- Linking Linear or Jira tickets from the dashboard. Those repos get no ticket link, as today for any tracker other than GitHub.
- Editing Fathom's `project.md` or the template.
- The status-pane mod and the Python scripts.

## Calls I made

- **An unknown tracker value reads as not GitHub, with no error.** `project_config.py` exits on a value outside `linear`, `github`, `jira`. The dashboard must not stop serving `/api` over a typo, so any value other than `github` just turns issue links off.
- **The value is lowercased**, as `project_config.py` does, so `` `GitHub` `` counts as `github`.
- **The first matching row wins**, as in `project_config.py`. A second `Tracker` row later in the file is ignored.
- **The test sits on `repoUrlFromProject` only.** The ticket names the three consumers, but they already read the flag and have their own tests for the `false` case (for example the `not issues` row in `api.test.ts`), so testing the parse covers the bug.

## Touches

None of these: data, money, auth, user email, migrations.
