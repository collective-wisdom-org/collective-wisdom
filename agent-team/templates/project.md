# Project config (<product name>)

The one place for repo-specific facts. The agent-team skills read this file instead of hardcoding them. `TODO(<owner>)` marks a value that is not decided yet; an agent that needs one must not guess (in team mode, stop with `BLOCKED:`).

Scripts read the first backticked token in each Value cell, so keep the backticks around the real value and keep notes free of extra backticks in the cells marked below.

## Identity

| Key | Value |
|---|---|
| Product name | <product name and one-line description> |
| Tracker (`linear`, `github` or `jira`) | `linear` |
| Tracker scope (`<TEAM>`) | <Linear team name, the GitHub repo, or the Jira project key> |
| Linear team name (Linear only) | <team name> (key `<PREFIX>`, <https://linear.app/<workspace>/team/<PREFIX>/overview>) |
| Issue identifier prefix (`<PREFIX>`) | `<PREFIX>` |
| Linear project (Linear only) | <project name, or none (the team is the scope)> |
| Approver | <name>. Approves specs and merges only |

### Choosing a tracker

Set the `Tracker` row to `linear`, `github` or `jira`. A missing row or a `TODO(...)` value means `linear`. Operations and adapters: [trackers/README.md](trackers/README.md).

- `github`: no extra rows. Tickets are GitHub issues in the `Repo` below, and `Issue identifier prefix` is any short prefix (for example `GH`). The `./scripts/gh.sh` wrapper does every call.
- `jira`: untested. Add these rows to the table above and fill them in:

```
| Jira site | `https://example.atlassian.net` |
| Jira project key | `ABC` |
| Jira status: Backlog | `Backlog` |
| Jira status: Todo | `To Do` |
| Jira status: In Progress | `In Progress` |
| Jira status: In Review | `In Review` |
| Jira status: Done | `Done` |
| Jira status: Canceled | `Canceled` |
```

## Git and GitHub

| Key | Value |
|---|---|
| Branch pattern | `feat/<prefix>-N-short-title` (`<prefix>` is the issue prefix in lower case) |
| Repo (`<owner>/<repo>`) | `<owner>/<repo>` (<https://github.com/<owner>/<repo>>) |
| Owner login (trusted review-comment author) | `<github-login>` |
| Chief of Staff login | `none` (the account that files and moves tickets as the Chief of Staff; set it once the account exists and is added to gh, see [github-auth.md](github-auth.md) § Agent users; an app may leave all four as none) |
| Builder login | `none` (the ship-loop child's account: PRs, notes and its own ticket; same setup; an app may leave all four as none) |
| Code reviewer login | `none` (the account that posts the code review comment; same setup; an app may leave all four as none) |
| Security reviewer login | `none` (the account that posts the security review comment; same setup; an app may leave all four as none) |
| GitHub CLI | `./scripts/gh.sh` only, never bare `gh`. Setup: [github-auth.md](github-auth.md) |
| Commits | Conventional: `feat:`, `fix:`, `docs:`, `infra:` |

## Commands

| Key | Value |
|---|---|
| Test | `<test command>` |
| Lint | <command, or TODO(<owner>)> |
| Typecheck | <command, or TODO(<owner>)> |
| Required CI checks | <check names, or TODO(<owner>)> |
| Agent-team script tests | `python3 -I -m pytest -q scripts` (needs `pytest`, e.g. `uvx pytest -q scripts`) |
| Docs index listing | `python3 scripts/docs_index.py` (prints every `docs/superpowers/index/*.md` entry as one table) |
| Release notes listing | `python3 scripts/release_notes.py` (prints every `docs/superpowers/release-notes/*.md` note, newest first) |
| Test database | none (or how to create the per-ticket test database; never test or migrate against the dev database) |
| Migration heads check | none (or the command, e.g. a migration tool's heads listing) |
| Migrations directory | none (or a path in backticks; scripts read the first backticked path, so keep any note free of backticks. Clash checks expect files named NNN_name.py there) |

## Repo invariants

Skills and the Chief of Staff restate these in every child task.

- The root checkout stays on `main`. Branch work happens in a worktree: `.worktrees/<short-name>/`, or the one T3 Code created under `~/.t3/worktrees/`.
- Never push to `main`; push only the ticket's own `feat/<prefix>-N-*` branch.
- Never commit `.env`, API keys or tokens.
- <Name the local data directories that must never be deleted, and the docker rules (for example, no `docker compose up` from a worktree, no `down -v`). Add any other repo-specific rules.>

## Areas and labels

- Area labels: <e.g. `frontend`, `backend`, `infra`>. Type labels: `Feature`, `Improvement`, `Bug`. Team labels `agent` and `agent-skip` are managed by the Chief of Staff and the approver.
- Areas (path boundaries per role): <paths per role, or none>.

## Product rules

- Brand in the interface: <name>.
- <Rules every ticket must follow: default currency, data scoping, visual system.>

## Security overlays

Extra checks for the security review, on top of OWASP and "no secrets in repo".

- <e.g. tenant or user scoping on every query, server-side admin checks.>

## Docs

| Key | Value |
|---|---|
| Specs / plans / as-built | `docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/superpowers/as-built/` |
| Index | One file per ticket in `docs/superpowers/index/<prefix>-N.md` (docs with no ticket: `index/<YYYY-MM-DD>-<slug>.md`); layout in [`docs/superpowers/README.md`](../superpowers/README.md) |
| Release notes | One file per ticket in `docs/superpowers/release-notes/<prefix>-N.md` (docs with no ticket: `release-notes/<YYYY-MM-DD>-<slug>.md`); layout in [`docs/superpowers/README.md`](../superpowers/README.md) |

## Docs check

Read by the documenter subagent ([documenter.md](documenter.md)).

- Living docs to search: `README.md`, `AGENTS.md`, `docs/agents/`, `.claude/skills/`, <add the architecture doc, infra README, env example file and so on, or remove what the repo lacks>.
- Extra checks: <e.g. "brand docs in `docs/brand/` when the diff touches theme tokens, logo, fonts or colours", or none>.

## Environments and deploy

- <Environments, deploy target, who deploys.>

## Models

Defaults live in the `chief-of-staff` skill, section Models. They are defaults, not repo rules; change them by ticket and PR.
