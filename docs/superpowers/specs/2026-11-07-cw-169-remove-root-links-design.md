# CW-169: Remove this repo's root links into agent-team and rely on the machine install

**Status:** Shipped
**Shipped:** in PR #170, as specified
**Ticket:** [#169](https://github.com/collective-wisdom-org/collective-wisdom/issues/169)
**Follows:** CW-160 to CW-163 (machine install at `~/.collective-wisdom`, apps commit only `docs/agents/project.md`).

## Goals

This repo runs the team the way an app does: from the machine install at `~/.collective-wisdom`, with no tracked links into `agent-team/`. Shared files keep one home, `agent-team/`, and one path to reach them from a session, the machine install.

## Today

Facts from `main` at `3073757`.

- `git ls-files -s | grep '^120000'` lists 18 links: `.claude/skills`, `.claude/agents`, `.claude/settings.json`, `.agents/skills` (to `../.claude/skills`), `scripts`, `docs/superpowers/README.md`, and every entry of `docs/agents/` except `project.md` (11 role docs and `trackers`).
- `install.sh` links `~/.collective-wisdom` to the root checkout's `agent-team/`, links the skills and agents into `~/.claude`, `~/.agents` and `~/.cursor`, and merges a Stop hook (`python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook`) into `~/.claude/settings.json`.
- The root `.claude/settings.json` link points at `agent-team/.claude/settings.json`, which holds a second Stop hook, `$CLAUDE_PROJECT_DIR/scripts/cos_rotation_check.py`. Here the hook runs twice. Nothing else reads that file: `install.sh` does not copy it, and `remove_app_copies.py` only prints a TODO about an app's own copy.
- `agent-team/scripts/test_root_links.py` checks that the links resolve, that every shared role doc is linked, that `project.md` is local, and that the six named links point into `agent-team/`.
- CI (`.github/workflows/ci.yml`) and the test command run `agent-team/scripts` by path. No test besides `test_root_links.py` goes through a root link: `test_agent_files.py` and `test_call_sites.py` read under `agent-team/`, and `test_symlinked_root.py` builds its own temp layout.
- `cos_rotation_check.py` reads its `SKILL_PATHS` under `agent-team/` (the resolved clone), not through the root links.
- The links are named, or the removed paths used, in: `AGENTS.md` (Product, GitHub, Required reading, Testing, Agent config), `CONTRIBUTING.md`, `README.md` (Layout, Running a Chief of Staff in this repo, Requirements, Review mode, Choosing a tracker, Agent pane), `docs/agents/project.md` (tracker links, GitHub CLI, Commands, Repo invariants, Docs, Docs check), `agent-team/docs/agents/chief-of-staff.md` line 11, `agent-team/.claude/skills/chief-of-staff/approvals.md` (the `scripts` root link), `agent-team/docs/agents/trackers/README.md` (bare `scripts/test_tracker_docs.py`, `scripts/project_config.py`, allowed by an `EDITED` exception in `test_call_sites.py`), and `agent-team/docs/superpowers/README.md` (bare `python3 scripts/docs_index.py`, `scripts/release_notes.py`, `scripts/merge_pr.py`).

## Builds

### 1. Delete the links and the file only they used

- `git rm` the 18 links listed under Today. `docs/agents/` then holds only `project.md`, and `.claude/` and `.agents/` leave the tree.
- Delete `agent-team/.claude/settings.json`. Its only reader was the root link, and its hook duplicates the one `install.sh` adds. The Stop hook then runs once here.

### 2. Tests

- Delete `agent-team/scripts/test_root_links.py`.
- Add one test to `agent-team/scripts/test_agent_files.py`: `docs/agents/project.md` at the repo top is a real file, not a link, and `agent-team/docs/agents/project.md` does not exist. It sits under the module's existing "collective-wisdom root only" skip.
- In `test_call_sites.py`, drop the `EDITED` exception: the trackers README will name `agent-team/scripts/...`, which the script-call rule already ignores.

### 3. Paths in this repo's docs

Every command and path points at the machine install, or at `agent-team/` when the text tells a contributor which source file to edit.

- `AGENTS.md`: first lines say to run `./install.sh` once on the machine before anything else. Product says shared files live in `agent-team/` and sessions reach them through `~/.collective-wisdom`, with no root links. GitHub uses `~/.collective-wisdom/scripts/gh.sh` and `~/.collective-wisdom/docs/agents/github-auth.md`. Required reading points at `~/.collective-wisdom/docs/agents/...` for the role docs and keeps `docs/agents/project.md`. Testing names `test_agent_files.py` and `test_call_sites.py` instead of `test_root_links.py`. Agent config says skills and subagents load from the machine install (`~/.claude/skills`, `~/.claude/agents`, `~/.agents/skills`, `~/.cursor/skills`), and are edited under `agent-team/.claude/`.
- `docs/agents/project.md`: tracker and auth links become `~/.collective-wisdom/docs/agents/...` code paths (a relative link now points at nothing). `GitHub CLI`, `Docs index listing`, `Release notes listing`, the `merge_pr.py` mentions in Repo invariants and Docs, and the `Index` row use `~/.collective-wisdom/scripts/...` and `~/.collective-wisdom/docs/superpowers/README.md`. The `Agent-team script tests` note drops "`scripts/` at the root is a link". The invariant becomes: run `./install.sh` once on the machine; edit shared files under `agent-team/`; the repo has no root links, and `docs/agents/project.md` is its only file under `docs/agents/`. Docs check lists `docs/agents/project.md` and keeps `agent-team/docs/agents/` (see Calls I made).
- `CONTRIBUTING.md`: the edit rule says shared files are edited under `agent-team/` and that `./install.sh` must have run once; no mention of root links.
- `README.md`: Layout drops the `agent-team/.claude/settings.json` row and names `~/.collective-wisdom/scripts/docs_index.py`. "Running a Chief of Staff in this repo" is rewritten: run `./install.sh` from the root checkout once, then run the Chief of Staff from the root checkout on `main` like in an app; sessions here, worktrees included, run the root checkout's skills and scripts, so a branch's skill or script change is live only after it merges and the root checkout fast-forwards; tests run `agent-team/scripts` by path, so a branch's own scripts are tested; `docs/agents/project.md` is local and never shipped; a permission a tool saves to `.claude/settings.json` now stays this repo's own file (commit it only if everyone working here should get it; personal ones go in `.claude/settings.local.json`). Requirements, Review mode and Choosing a tracker use `~/.collective-wisdom/scripts/...`. The Agent pane line says the mod reads `scripts/prices.json` from the session's folder, so in an app, and now in this repo, the cost column shows a dash.
- `agent-team/docs/agents/chief-of-staff.md`: line 11 says collective-wisdom reads them the same way, after `./install.sh`.
- `agent-team/.claude/skills/chief-of-staff/approvals.md`: "the bare name of the `scripts` root link" becomes "a path that is just `scripts` (a link to the scripts folder)". The rule in `approval_policy.py` does not change.
- `agent-team/docs/agents/trackers/README.md`: the two source files become `agent-team/scripts/test_tracker_docs.py` and `agent-team/scripts/project_config.py`.
- `agent-team/docs/superpowers/README.md`: the three commands become `~/.collective-wisdom/scripts/...`.

### 4. How this build runs once the links are gone

- The child's skills, subagents and `gh.sh` already come from `~/.claude/skills` and `~/.collective-wisdom`, the root checkout on `main`. Deleting the links on the branch changes nothing for the session building it.
- Tests: `python3 -I -m pytest -q agent-team/scripts` and the shellcheck line, by path, as now. CI runs the same.
- Checks before the PR: `git ls-files -s | grep '^120000'` is empty; `python3 ~/.collective-wisdom/scripts/docs_index.py` and `~/.collective-wisdom/scripts/gh.sh auth status` run from the worktree top; a grep outside `docs/superpowers/` and `agent-team/docs/superpowers/{specs,plans,as-built}/` finds no `./scripts/`, bare `scripts/x.py` call, `docs/agents/<role doc>` path at the root, `docs/superpowers/README.md` link, or "root link" as something that exists.

## Leaves out

- What `install.sh` installs or how it links in `$HOME`.
- A check that the machine install exists. On a fresh clone without it, the first `~/.collective-wisdom/scripts/...` call fails with "No such file", and `AGENTS.md` says in its first lines to run `./install.sh`. Apps already behave this way.
- The `agent-gantt` mod's cost column. It reads `scripts/prices.json` relative to the session's folder, so it already shows a dash in every app, and will here too. Pointing it at `~/.collective-wisdom/scripts/prices.json` is a mod change with its own version bump; worth its own ticket.
- Stale T3 worktrees under `~/.t3/worktrees/` that still have the links.
- Old specs, plans and as-built records under `docs/superpowers/` and `agent-team/docs/superpowers/{specs,plans,as-built}/`.
- `approval_policy.py`: it still treats a bare `scripts` path and anything under `.claude/`, `scripts/` and `docs/agents/` as the approval path, so this PR is never auto-approved.

## Acceptance

- `git ls-files -s | grep '^120000'` lists nothing, and `agent-team/.claude/settings.json` is gone.
- On a machine with `./install.sh` run, from the root checkout after merge: a Chief of Staff skill is invocable, `~/.collective-wisdom/scripts/gh.sh auth status` and `python3 ~/.collective-wisdom/scripts/docs_index.py` run from the repo top, and `~/.claude/settings.json` holds the only Stop hook for `cos_rotation_check.py`.
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.
- No file outside the old records says "root links" as a thing that exists, or points at `./scripts/`, `docs/agents/org-chart.md` or another removed path.

## Testing

- One new test in `test_agent_files.py` (project.md is local and never under `agent-team/`). It fails if someone links `project.md` or copies it into `agent-team/`.
- `test_call_sites.py` keeps its rules with the `EDITED` exception gone; it fails if the trackers README goes back to a bare `scripts/` path.
- No test for "no symlinks in the repo": the ticket drops link tests, and a reintroduced link breaks nothing the team runs.

## Calls I made

- **Delete `agent-team/.claude/settings.json`.** The ticket doesn't name it. The root link was its only reader, its hook duplicates the machine one, and leaving it would be a shipped file nothing uses.
- **Docs check keeps `agent-team/docs/agents/` and lists `docs/agents/project.md`, not `~/.collective-wisdom/docs/agents/`** as the ticket says. The documenter checks the PR branch; `~/.collective-wisdom` is the root checkout on `main`, so it would read the old copy of every role doc the PR changes.
- **Paths in `project.md` become code paths, not markdown links.** A `~/...` link does not resolve on GitHub or in an editor, and a relative one points at nothing once the links are gone.
- **Contributor "edit this file" pointers name `agent-team/scripts/...`,** not `~/.collective-wisdom/...`: you edit the source on your branch, not the root checkout's copy. That lets `test_call_sites.py` drop its `EDITED` exception.
- **README says a branch's skill and script changes go live only after merge.** This was already true for scripts (CW-160); the root `.claude/skills` link used to make a worktree load its own branch's skills, and that goes away.
- **The `agent-gantt` cost dash is left as is** (see Leaves out), and `approvals.md`'s wording changes while `approval_policy.py` does not.
- **The project.md test goes in `test_agent_files.py`** (as the ticket says) under its existing root-only skip.

## Touches

None of these: no data, money, auth, user email or migrations.
