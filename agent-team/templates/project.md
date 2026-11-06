# Project config (<product name>)

The one place for repo-specific facts. The agent-team skills read this file instead of hardcoding them. `TODO(<owner>)` marks a value not decided yet; an agent that needs one must not guess (stop with `BLOCKED:`).

Scripts read the first backticked token in each Value cell. Keep the backticks around the real value, and keep notes free of extra backticks in the cells marked below.

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
| Approval risk tolerance (`strict`, `balanced` or `permissive`) | `strict`. Which approvals the team takes without asking: `strict` none, `balanced` Low risk only, `permissive` Low and Medium. High always waits for you |
| Claude subscription API-equivalent usage (dollars) | `none`. Set it to the API-equivalent dollars the Claude plan shows (a number such as 12000); ticket costs then show a share of it |
| Review after conflict resolution (`off` or `on`) | `off`. Whether a conflict resolution is reviewed again before it can merge. `off`: reviews from before the resolution stand, and a merge you already approved goes ahead on the resolved head without asking again. `on`: code and security review run on the resolved head, and you approve it again |

### Choosing a tracker

Set the `Tracker` row to `linear`, `github` or `jira`. A missing row or a `TODO(...)` value means `linear`. Operations and adapters: [trackers/README.md](trackers/README.md).

- `github`: no extra rows. Tickets are GitHub issues in the `Repo` below, and `Issue identifier prefix` is any short prefix (for example `GH`). The `./scripts/gh.sh` wrapper does every call.
- `jira`: untested. Add the rows listed in [trackers/jira.md](trackers/jira.md) § project.md rows to the table above and fill them in.

## Git and GitHub

| Key | Value |
|---|---|
| Branch pattern | `feat/<prefix>-N-short-title` (`<prefix>` is the issue prefix in lower case) |
| Repo (`<owner>/<repo>`) | `<owner>/<repo>` (<https://github.com/<owner>/<repo>>) |
| Owner login (trusted review-comment author) | `<github-login>` |
| Require teammate approval (`on` or `off`) | `off`. When on, merge_pr.py also needs an approving GitHub review on the current head from an owner, member or collaborator other than the PR author. A missing row means off |
| GitHub CLI | `./scripts/gh.sh` only, never bare `gh`. Setup: [github-auth.md](github-auth.md) |
| Commits | Conventional: `feat:`, `fix:`, `docs:`, `infra:` |

## Commands

| Key | Value |
|---|---|
| Test | `<test command>` |
| Lint | <command, or TODO(<owner>)> |
| Typecheck | <command, or TODO(<owner>)> |
| Required CI checks | <check names, or `none (no CI yet)` when the repo has no CI, or TODO(<owner>)> |
| Agent-team script tests | `python3 -I -m pytest -q scripts` (needs `pytest`, e.g. `uvx pytest -q scripts`) |
| Docs index listing | `python3 scripts/docs_index.py` (generates one table of every spec, plan and as-built under `docs/superpowers/`) |
| Release notes listing | `python3 scripts/release_notes.py` (prints the `## Release note` sections of merged PRs and any `docs/superpowers/release-notes/*.md` notes, newest first) |
| Test database | none (or how to create the per-ticket test database; never test or migrate against the dev database) |
| Migration heads check | none (or the command, e.g. a migration tool's heads listing) |
| Migrations directory | none (or a path in backticks; scripts read the first backticked path, so keep any note free of backticks. Clash checks expect files named NNN_name.py there) |

## Review

| Key | Value |
|---|---|
| Review mode (`agents` or `ci`) | `agents`. `ci` uses the review bot in CI instead of the code and security reviewer agents. A missing row means `agents` |
| CI review bot login (`ci` mode only) | none (or the bot's GitHub login in backticks; keep any note free of other backticks, since scripts read the first one) |
| CI review skill (`ci` mode only, optional) | none (or the name of a globally installed skill to follow when replying to the bot's findings) |

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
| Index | Generated by `python3 scripts/docs_index.py` from `specs/`, `plans/` and `as-built/`; nothing to edit by hand. Layout in [`docs/superpowers/README.md`](../superpowers/README.md) |
| Publish release notes (`on` or `off`) | `off`. With `on`, each PR body has a `## Release note` section and every merge publishes all notes to `RELEASE_NOTES.md` on the `release-notes` branch (`https://github.com/<owner>/<repo>/blob/release-notes/RELEASE_NOTES.md`, `Repo` above); older notes stay in `docs/superpowers/release-notes/`. `scripts/merge_pr.py` is then the one writer of that branch, through the GitHub API after a merge; no agent, skill or other script writes it, by push or by API. A missing row reads as `on`. Layout in [`docs/superpowers/README.md`](../superpowers/README.md) |

## Docs check

Read by the documenter subagent ([documenter.md](documenter.md)).

- Living docs to search: `README.md`, `AGENTS.md`, `docs/agents/`, `.claude/skills/`, <add the architecture doc, infra README, env example file and so on, or remove what the repo lacks>.
- Extra checks: <e.g. "brand docs in `docs/brand/` when the diff touches theme tokens, logo, fonts or colours", or none>.

## Environments and deploy

- <Environments, deploy target, who deploys.>

## Models

Defaults live in the `chief-of-staff` skill, section Models. They are defaults, not repo rules; change them by ticket and PR.
