# collective-wisdom

Shared agent workflows, skills and scripts for a set of apps.

## What this is

An agent team that moves tickets (in Linear, GitHub Issues or Jira) from spec to merge. A Chief of Staff thread keeps tickets moving through the ship loop (kickoff, build, open PR, security review, merge) in child T3 Code threads. A project manager pass ranks the backlog and tidies the tracker. Reviews and the OWASP security pass happen before every merge, and the human approves only the spec and the merge. Who does what is in [agent-team/docs/agents/org-chart.md](agent-team/docs/agents/org-chart.md).

Nothing here is specific to one app. Each app keeps its own facts (ticket prefix, repo, test command, invariants) in `docs/agents/project.md`, and the skills and scripts read that file.

## Layout

`agent-team/` mirrors a consuming repo, so every path inside the skills, scripts and docs stays valid after install.

- `agent-team/.claude/skills/`: the team skills (chief-of-staff, project-manager, ship-loop, kickoff-feature, build-from-plan, open-pr, security-review, merge-pr, write-ticket) and the supporting ones (human-writing, owasp-security, agent-security, auditing-security)
- `agent-team/.claude/agents/`: the documenter, implementer, code-reviewer and security-reviewer subagents, each a pointer to its role doc
- `agent-team/.claude/settings.json`: the Stop hook for `cos_rotation_check.py`
- `agent-team/scripts/`: the team scripts, their tests, `gh.sh` and `wait-for-ci.sh`
- `agent-team/docs/agents/`: shared role docs (including the documenter)
- `agent-team/docs/superpowers/README.md`: the docs index convention
- `agent-team/templates/`: starting points for `docs/agents/project.md`, `AGENTS.md` and the `.gitignore` lines
- `install.sh`: installs or updates the team in a repo, and writes `docs/agents/installed-from.txt` in the app (the version pin)

## Running a Chief of Staff in this repo

This repo runs its own Chief of Staff. The root links into `agent-team/` so the skills, scripts and docs sit at the paths they expect, with one copy of each: `.claude/skills`, `.claude/agents`, `.claude/settings.json`, `scripts`, `.agents/skills`, `docs/superpowers/README.md`, and each entry of `docs/agents/` except `project.md`.

- `docs/agents/project.md` is real and local to this repo (tracker `github`, prefix `CW`). It is never shipped; apps are seeded from `agent-team/templates/project.md`.
- Edit shared files under `agent-team/`, never through the links.
- `.claude/settings.json` at the root is a link into `agent-team/.claude/settings.json`, so any permission a tool saves to project settings lands in the shipped file; put personal permissions in `.claude/settings.local.json` (gitignored).
- Run the Chief of Staff from the root checkout on `main`, like in an app. `agent-team/scripts/test_root_links.py` fails on a dangling link or an unlinked doc.

## Requirements

- T3 Code, for the Chief of Staff and child threads (the skills call its thread tools)
- A ticket tracker: Linear (the Linear MCP), GitHub Issues (no extra tool) or Jira (the Atlassian Rovo MCP). See Choosing a tracker
- GitHub CLI (`gh`), used through `scripts/gh.sh`; see `agent-team/docs/agents/github-auth.md`
- Python 3 and `pytest` (for example `uvx pytest`) to run the script tests
- Superpowers skills used by the ship loop: `brainstorming`, `writing-plans`, `using-git-worktrees`, `executing-plans`, `subagent-driven-development`, `verification-before-completion` and `finishing-a-development-branch`

## Install

From a clone of this repo:

```sh
./install.sh --dry-run /path/to/app   # preview
./install.sh /path/to/app             # install
```

The target must be a git repo with no uncommitted changes in the paths the installer touches. This clone must be a git repo with a clean working tree too, in dry-run as well as a real run, because the install is pinned to its `HEAD`. It copies the skills, scripts and shared docs, links `.agents/skills` to `../.claude/skills`, and adds missing lines to `.gitignore`. It never overwrites an existing `docs/agents/project.md`, `AGENTS.md` or `.claude/settings.json`. If `project.md` or `AGENTS.md` is missing it seeds one from `agent-team/templates/` and prints what to fill in. Commit the result in the app.

The installer also writes `docs/agents/installed-from.txt` in the app: one line, `collective-wisdom <full commit SHA>`. Commit it with the install, and check it to see which version an app runs.

After syncing skills it warns about any folder in the app's `.claude/skills/` that it did not ship and whose name ends with a shipped skill's name (for example `acme-ship-loop` next to `ship-loop`). That is an old copy from before the app installed from here. The installer never deletes anything; remove the folder yourself.

## Configure a consuming repo

Edit `docs/agents/project.md` in the app and replace every `<placeholder>`. The scripts read the first backticked token in a Value cell, so at least the issue identifier prefix, the repo, the branch pattern and the test command need real values. Anything marked `TODO(...)` is read as unset, and agents will stop rather than guess.

## Choosing a tracker

The `Tracker` row in `docs/agents/project.md` § Identity picks where tickets live: `linear`, `github` or `jira`. A repo with no row uses `linear`, so existing installs keep working. New installs get the row from the template.

- `linear`: the default. Needs the Linear MCP and the Linear rows in `project.md`.
- `github`: tickets are GitHub issues in the repo, driven through `./scripts/gh.sh`. States and priority are labels.
- `jira`: through the Atlassian Rovo MCP. Untested: nobody with Jira access has run it, so treat it as a starting point.

Skills describe each step as an operation ("set the ticket to In Review"), and one adapter doc per tracker in `agent-team/docs/agents/trackers/` says how to do it. Switching an existing app to another tracker is not automated: open tickets, `.agent-team/state.json` and the `agent` labels do not move. Switch only with the team stopped and the state file empty.

## Update

Pull this repo, then re-run `./install.sh /path/to/app`. It is idempotent and updates skills, scripts and shared docs in place, and rewrites `docs/agents/installed-from.txt` when `HEAD` has moved. Commit the update in the app as an install PR. If `.claude/settings.json` differs from the shipped one it is left alone and the script tells you to merge the hook by hand.

## Propose changes

Open a PR here, not in the app. Run the script tests with `uvx pytest -q agent-team/scripts` (CI does the same). After it merges, pull and re-run `install.sh` in each app; each app's install PR bumps `docs/agents/installed-from.txt`. Prose follows the `human-writing` skill: plain sentences, no em dashes.

## Known couplings

- T3 Code thread tools are named directly in the Chief of Staff, project manager and ship-loop skills. Tracker tools are named only in the adapter docs under `agent-team/docs/agents/trackers/`.
- Plans, specs and as-built notes follow the superpowers docs layout under `docs/superpowers/`.
- The security review skill refers to Cursor's review-security subagent and Claude Code's `/security-review`.
- Role docs for app areas (backend, frontend and so on) are not shared; each app adds its own.
