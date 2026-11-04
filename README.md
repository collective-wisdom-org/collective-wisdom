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
- `install.sh`: installs, updates and drift-checks the team in a repo, and writes `docs/agents/installed-from.txt` in the app (the version pin)

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
./install.sh --to <ref> /path/to/app  # install a given commit instead of this clone's HEAD
```

The target must be a git repo with no uncommitted changes in the paths the installer touches. The files come from a commit of this repo, not from its working tree, so this clone can have uncommitted changes. The commit is this clone's `HEAD`, or `<ref>` (a SHA, a branch, anything `git rev-parse` takes), and it must be on `origin/main`: an app is never pinned to an unmerged branch. A clone with no fetched `origin/main` is refused until you run `git fetch origin` there. The installer copies the skills, scripts and shared docs, links `.agents/skills` to `../.claude/skills`, and adds missing lines to `.gitignore`. It never overwrites an existing `docs/agents/project.md`, `AGENTS.md` or `.claude/settings.json`. If `project.md` or `AGENTS.md` is missing it seeds one from `agent-team/templates/` and prints what to fill in. Commit the result in the app.

The installer also writes `docs/agents/installed-from.txt` in the app: one line, `collective-wisdom <full commit SHA>`. Commit it with the install. It is the version pin: the update and the drift check read it.

After syncing skills it warns about any folder in the app's `.claude/skills/` that it did not ship and whose name ends with a shipped skill's name (for example `acme-ship-loop` next to `ship-loop`). That is an old copy from before the app installed from here. The installer never deletes anything; remove the folder yourself.

### Check for drift

```sh
./install.sh --check /path/to/app
```

This compares the skills, agents, scripts and shared docs in the app with the commit in `installed-from.txt` and writes nothing. It prints `changed  <path>` or `missing  <path>` for each difference and ends with `check: matches collective-wisdom <sha>` (exit 0) or `check: drift in N file(s) against collective-wisdom <sha>` (exit 1). It exits 2 when it can't check: no pin, a malformed pin, or a commit this clone doesn't have (run `git fetch origin` here). Files the app owns (`project.md`, `AGENTS.md`, `settings.json`, its own skills and scripts) are not compared.

## Configure a consuming repo

Edit `docs/agents/project.md` in the app and replace every `<placeholder>`. The scripts read the first backticked token in a Value cell, so at least the issue identifier prefix, the repo, the branch pattern and the test command need real values. Anything marked `TODO(...)` is read as unset, and agents will stop rather than guess.

## Choosing a tracker

The `Tracker` row in `docs/agents/project.md` § Identity picks where tickets live: `linear`, `github` or `jira`. A repo with no row uses `linear`, so existing installs keep working. New installs get the row from the template.

- `linear`: the default. Needs the Linear MCP and the Linear rows in `project.md`.
- `github`: tickets are GitHub issues in the repo, driven through `./scripts/gh.sh`. States and priority are labels.
- `jira`: through the Atlassian Rovo MCP. Untested: nobody with Jira access has run it, so treat it as a starting point.

Skills describe each step as an operation ("set the ticket to In Review"), and one adapter doc per tracker in `agent-team/docs/agents/trackers/` says how to do it. Switching an existing app to another tracker is not automated: open tickets, `.agent-team/state.json` and the `agent` labels do not move. Switch only with the team stopped and the state file empty.

## Update

```sh
./install.sh --update /path/to/app              # move to origin/main
./install.sh --update --to <ref> /path/to/app   # move to a given commit
./install.sh --dry-run --update /path/to/app    # preview
```

`--update` without `--to` fetches `origin` in this clone and moves to `origin/main`, so you don't need to pull first. With `--to <ref>` it does not fetch, so the commit must already be in this clone. It needs the app's `installed-from.txt`; without one, run a plain install. Before copying it runs the drift check against the old pin. If the app's copies were edited by hand, it lists the files and stops, because the update would overwrite them. Move the edits into this repo first, or add `--force` to overwrite them.

Then it copies the new commit's files, rewrites `installed-from.txt` and prints a report:

```
collective-wisdom 1a2b3c4d5e6f -> 9f8e7d6c5b4a (14 commits)
  e835684 feat: stop restarting children that only wait on CI (CW-21) (#34)
update  .claude/skills/ship-loop/SKILL.md
add     scripts/pr_diff_delta.py
TODO:
  - Delete scripts/old_thing.py: collective-wisdom no longer ships it (shipped at 1a2b3c4d5e6f, gone at 9f8e7d6c5b4a).
```

The commit list covers `agent-team/` only. A `Delete` TODO names a file the old commit shipped and the new one doesn't. The installer never deletes, so removing it is the app's job. At the same commit with no drift it prints `already at <sha>, nothing to do`. Commit the update in the app as an install PR. If `.claude/settings.json` differs from the shipped one it is left alone and the script tells you to merge the hook by hand.

## Propose changes

Open a PR here, not in the app. Run the script tests with `uvx pytest -q agent-team/scripts` (CI does the same). After it merges, run `install.sh --update` in each app; each app's install PR bumps `docs/agents/installed-from.txt`. Prose follows the `human-writing` skill: plain sentences, no em dashes.

## Known couplings

- T3 Code thread tools are named directly in the Chief of Staff, project manager and ship-loop skills. Tracker tools are named only in the adapter docs under `agent-team/docs/agents/trackers/`.
- Plans, specs and as-built notes follow the superpowers docs layout under `docs/superpowers/`.
- The security review skill refers to Cursor's review-security subagent and Claude Code's `/security-review`.
- Role docs for app areas (backend, frontend and so on) are not shared; each app adds its own.
