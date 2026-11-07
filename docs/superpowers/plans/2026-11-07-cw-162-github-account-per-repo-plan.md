# CW-162 plan: choose the GitHub account per repo

Spec: [design](../specs/2026-11-06-cw-162-github-account-per-repo-design.md). Shared files are edited under `agent-team/`; `README.md` sits at the root and `docs/agents/project.md` is this repo's own. The spec's section numbers are used below.

## Tasks

Two write scopes, disjoint, so they run in parallel.

### A. Scripts and tests (scope: `agent-team/scripts/`, `agent-team/templates/user.md`)

1. `user_config.py` (spec § 2): `path()`, `repo_key(root)`, `login(root)`, `subscription_usage(provider)` and the `account` / `path` CLI. Parse like `project_config` (first backticked token per cell). Malformed login or a duplicate row for the repo raises with the file and line; no file or no row is None.
2. `agent-team/templates/user.md` (spec § 1 shape, verbatim).
3. `gh.sh` (spec § 3): ask `python3 -I user_config.py account` (found next to `gh.sh` through the script's own folder, following links); no account runs gh as today; a mapped account passes `gh auth token --hostname <host> --user <login>` as `GH_TOKEN` (`GH_ENTERPRISE_TOKEN` for hosts other than `github.com` and `*.ghe.com`) for that one command; a failed or empty token prints the spec's error, exits 2 and runs nothing. No `gh auth switch`. Passes shellcheck.
4. `merge_pr.py`, `cos_approve_pr.py`, `cos_untracked_check.py`, `agent_usage.py` (spec § 4, § 5): switch to `user_config`, with the two new gate messages. Delete `project_config.subscription_usage`.
5. Tests (spec § Testing): new `test_user_config.py` and extend `test_gh_sh.py`; move the fixtures of `conftest.py`, `test_merge_pr.py`, `test_cos_approve_pr.py`, `test_cos_untracked_check.py`, `test_agent_usage.py` and `test_project_config.py` (if it pins `subscription_usage`) from the two `project.md` rows to a temp `user.md` under a temp `HOME`. Table-driven; test lines do not exceed feature lines.

### B. Rows and docs (scope: `agent-team/templates/project.md`, `docs/agents/project.md`, `agent-team/docs/agents/`, `agent-team/.claude/skills/{merge-pr,chief-of-staff}/SKILL.md`, `README.md`)

1. Delete the `Owner login` and `Claude subscription API-equivalent usage` rows from both `project.md` files (spec § 5). Do not touch other rows.
2. `github-auth.md` new `## Account per repo` section, `merge-pr` and `chief-of-staff` skills, `trackers/github.md`, `README.md` and the `Layout` bullet (spec § 6). Plain sentences, no em dashes.

## Verify

```
python3 -I -m pytest -q agent-team/scripts
shellcheck install.sh tag-release.sh agent-team/scripts/*.sh
/usr/bin/grep -rn "Owner login" agent-team README.md docs/agents
```

The last command prints nothing but historic mentions in `docs/superpowers/`.
