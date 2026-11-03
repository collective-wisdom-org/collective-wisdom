# collective-wisdom

Shared agent workflows, skills and scripts for David's apps.

## What this is

An agent team that moves Linear tickets from spec to merge. A Chief of Staff thread keeps tickets moving through the ship loop (kickoff, build, open PR, security review, merge) in child T3 Code threads. A project manager pass ranks the backlog and tidies Linear. Reviews and the OWASP security pass happen before every merge, and the human approves only the spec and the merge. Who does what is in [agent-team/docs/agents/org-chart.md](agent-team/docs/agents/org-chart.md).

Nothing here is specific to one app. Each app keeps its own facts (ticket prefix, repo, test command, invariants) in `docs/agents/project.md`, and the skills and scripts read that file.

## Layout

`agent-team/` mirrors a consuming repo, so every path inside the skills, scripts and docs stays valid after install.

- `agent-team/.claude/skills/`: the team skills (chief-of-staff, project-manager, ship-loop, kickoff-feature, build-from-plan, open-pr, security-review, merge-pr, write-ticket) and the supporting ones (human-writing, owasp-security, agent-security, auditing-security)
- `agent-team/.claude/settings.json`: the Stop hook for `cos_rotation_check.py`
- `agent-team/scripts/`: the team scripts, their tests, `gh.sh` and `wait-for-ci.sh`
- `agent-team/docs/agents/`: shared role docs
- `agent-team/docs/superpowers/README.md`: the docs index convention
- `agent-team/templates/`: starting points for `docs/agents/project.md`, `AGENTS.md` and the `.gitignore` lines
- `install.sh`: installs or updates the team in a repo

## Requirements

- T3 Code, for the Chief of Staff and child threads (the skills call its thread tools)
- Linear MCP, for tickets
- GitHub CLI (`gh`), used through `scripts/gh.sh`; see `agent-team/docs/agents/github-auth.md`
- Python 3 and `pytest` (for example `uvx pytest`) to run the script tests
- Superpowers skills used by the ship loop: `brainstorming`, `writing-plans`, `using-git-worktrees`, `executing-plans`, `subagent-driven-development`, `verification-before-completion` and `finishing-a-development-branch`

## Install

From a clone of this repo:

```sh
./install.sh --dry-run /path/to/app   # preview
./install.sh /path/to/app             # install
```

The target must be a git repo with no uncommitted changes in the paths the installer touches. It copies the skills, scripts and shared docs, links `.agents/skills` to `../.claude/skills`, and adds missing lines to `.gitignore`. It never overwrites an existing `docs/agents/project.md`, `AGENTS.md` or `.claude/settings.json`. If `project.md` or `AGENTS.md` is missing it seeds one from `agent-team/templates/` and prints what to fill in. Commit the result in the app.

## Configure a consuming repo

Edit `docs/agents/project.md` in the app and replace every `<placeholder>`. The scripts read the first backticked token in a Value cell, so at least the issue identifier prefix, the repo, the branch pattern and the test command need real values. Anything marked `TODO(...)` is read as unset, and agents will stop rather than guess.

## Update

Re-run `./install.sh /path/to/app` after pulling. It is idempotent and updates skills, scripts and shared docs in place. If `.claude/settings.json` differs from the shipped one it is left alone and the script tells you to merge the hook by hand.

## Propose changes

Open a PR here, not in the app. Run the script tests with `uvx pytest -q agent-team/scripts` (CI does the same). After it merges, re-run `install.sh` in each app. Prose follows the `human-writing` skill: plain sentences, no em dashes.

## Known couplings

- T3 Code thread tools and Linear MCP tools are named directly in the Chief of Staff, project manager and ship-loop skills.
- Plans, specs and as-built notes follow the superpowers docs layout under `docs/superpowers/`.
- The security review skill refers to Cursor's review-security subagent and Claude Code's `/security-review`.
- Role docs for app areas (backend, frontend and so on) are not shared; each app adds its own.
