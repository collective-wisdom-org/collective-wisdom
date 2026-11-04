# CW-42: Pin, update and drift-check the agent team in apps

**Ticket:** [CW-42](https://github.com/dbeallor/collective-wisdom/issues/42)
**Status:** Draft

## Goal

The team stays harness-agnostic: `install.sh` keeps copying files into the app, where Claude Code, Cursor, Codex and any host that reads repo files find them. What changes:

- An app moves to a newer commit in one command (`install.sh --update`), pinned to an exact commit SHA, with a report of what changed.
- A drift check says whether an app's copied files still match the commit in `docs/agents/installed-from.txt`.
- The scripts find the app from the repo you run them in, not from where their file sits.

The user dropped the plugin idea (an earlier draft of this spec) in favor of this.

## Non-goals

- A Claude Code plugin, a marketplace, or any host-specific packaging.
- Updating any app. Each app runs the update in its own install PR.
- Deleting old files from an app. The installer still never deletes.
- Changing what the scripts or skills do, beyond how scripts find the app.
- Changing this repo's root links or how its Chief of Staff runs.

## Today

Facts from `main` at `e835684`.

- `install.sh [--dry-run] <app>` copies the files in this clone's working tree: `agent-team/.claude/skills`, `.claude/agents`, `scripts` and `docs/agents`. It seeds `project.md`, `AGENTS.md` and `docs/superpowers/README.md`, links `.agents/skills`, adds `.gitignore` lines, copies `.claude/settings.json` when the app has none, and writes `docs/agents/installed-from.txt` (`collective-wisdom <full SHA of HEAD>`). It refuses when this clone has uncommitted changes, because the pin names `HEAD`.
- Updating means: pull this clone, re-run `install.sh`. Nothing compares the app's files with the pinned commit, so a hand edit to a copied skill goes unnoticed and is overwritten on the next install without a word. Files that a newer commit no longer ships stay in the app, and nothing says so.
- Every script finds the app from its own location: `Path(__file__).absolute().parent.parent` (`project_config.py`, `cos_state.py`, `cos_idle_check.py`, `cos_parent_check.py`, `cos_rotation_check.py`, `cos_handoff.py`, `cos_ready_check.py`, `cos_merged_check.py`, `cos_sweep.py`, `cos_worktree_check.py`, `merge_pr.py`, `pr_diff_delta.py`, `docs_index.py`, `release_notes.py`, `agent_usage.py`). `wait-for-ci.sh` does `cd "$(dirname "$0")/.."`. So a script works only when its file sits in `<app>/scripts/`.
- `merge-pr` runs `<root checkout>/scripts/merge_pr.py` by absolute path, from wherever the caller is, so that the PR being merged can't supply its own gate. `merge_pr.py` finds the root checkout from its own path.
- `install.sh` has no tests.

## Design

### 1. Commands

```sh
./install.sh [--dry-run] [--to <ref>] <app>            # install, or re-install, at one commit
./install.sh [--dry-run] --update [--to <ref>] [--force] <app>   # move an installed app to a newer commit
./install.sh --check <app>                             # drift check, writes nothing
```

`<ref>` is anything `git rev-parse` takes (a SHA, `origin/main`, a branch). It is resolved to a full 40-character SHA, and that SHA is what gets copied and pinned.

- **Install** without `--to` uses this clone's `HEAD`, as today.
- **Update** without `--to` runs `git fetch origin` in this clone and uses `origin/main`. So an update no longer needs you to pull this clone first.
- Both refuse a commit that isn't on `origin/main` (`git merge-base --is-ancestor <sha> origin/main`), so an app is never pinned to an unmerged branch.

### 2. Files come from the commit, not the working tree

The installer extracts the target commit's `agent-team/` with `git archive <sha> agent-team | tar -x` into a temp folder and copies from there. The copied files are then exactly the pinned commit by construction, so the refusal on uncommitted changes in this clone goes away. The other refusals stay: the clone must be its own repo root, and the app must be a git repo with no uncommitted changes in the paths the installer touches.

The copy rules don't change: the same folders, the same seeds, `settings.json` left alone when it differs, `.agents/skills` linked, `.gitignore` lines appended, nothing deleted. `installed-from.txt` keeps its one-line format, `collective-wisdom <full SHA>`.

### 3. Drift check

`--check` reads the SHA from the app's `installed-from.txt`, extracts that commit's `agent-team/`, and compares each file the installer copies (skills, agents, scripts, shared `docs/agents/`) with the app's copy. Seeded files (`project.md`, `AGENTS.md`, `docs/superpowers/README.md`) and `settings.json` belong to the app after seeding and are not compared.

Output, one line per finding, then a last line:

```
changed  .claude/skills/ship-loop/SKILL.md
missing  scripts/cos_state.py
check: drift in 2 file(s) against collective-wisdom <sha>
```

Exit 0 and `check: matches collective-wisdom <sha>` when nothing differs. Exit 1 on drift. Exit 2 when it can't check: no `installed-from.txt`, a malformed line, or a SHA this clone doesn't have (the message says to `git fetch` here).

Extra files in the app (its own skills or scripts) are not drift and aren't reported.

### 4. Update

`--update` needs an existing `installed-from.txt`; without one it stops and says to run a plain install. Then:

1. Runs the drift check against the old pin. On drift it lists the files and refuses, because the update would overwrite local edits. `--force` overwrites them anyway. An old SHA this clone doesn't have is exit 2, same as `--check`.
2. Copies the new commit's files, as an install does, and rewrites `installed-from.txt`.
3. Reports what changed:

   ```
   collective-wisdom 1a2b3c4d5e6f -> 9f8e7d6c5b4a (14 commits)
     e835684 feat: stop restarting children that only wait on CI (CW-21) (#34)
     ...
   update  .claude/skills/ship-loop/SKILL.md
   add     scripts/pr_diff_delta.py
   TODO:
     - Delete scripts/old_thing.py: collective-wisdom no longer ships it (shipped at 1a2b3c4d5e6f, gone at 9f8e7d6c5b4a).
   ```

   The commit list is `git log --oneline <old>..<new> -- agent-team`. The deletions are files in the old commit's shipped set that the new one lacks, listed as TODOs; the installer never deletes them.

`--dry-run` works with all three modes and writes nothing.

### 5. Scripts find the app from the working repo

New module `agent-team/scripts/app_root.py` with one function, `root()`: `git rev-parse --show-toplevel` run in the current directory, or the current directory if that fails. It returns the root checkout when run there and the worktree when run in a worktree, which matches what `__file__` gives today for every caller that runs a script from the repo top.

Every `ROOT`, `DEFAULT`, `DEFAULT_FILE`, `DEFAULT_STATE`, `INDEX` and `NOTES` built from `__file__` uses it instead, including `project_config.DEFAULT` and `agent_usage.project_name`. Scripts call `gh.sh` from their own folder (`Path(__file__).parent / "gh.sh"`), as `cos_brief.py` does already. `PROJECT_MD` and `COS_STATE_FILE` keep overriding. `wait-for-ci.sh` does `cd "$(git rev-parse --show-toplevel)"` and calls `gh.sh` from its own folder.

`merge_pr.py` used to find the root checkout from its absolute path. The `merge-pr` skill's line becomes `cd <root checkout> && python3 scripts/merge_pr.py <N> <SHA>`: still the root checkout's copy, so the PR can't supply its own gate, and now also the root checkout's repo.

`project.md` stays per repo. It is never under `agent-team/` and never copied (a test already checks this repo; the install test checks an app gets the template, not this repo's file).

### 6. Docs

- `README.md` § Install and § Update: the three modes, `--to`, `--force`, what the update report means, and that a deletion TODO is the app's to act on.
- `ship-loop` § Team mode, Workflow files: the app's install PR runs `install.sh --update`, which bumps `installed-from.txt`.
- `merge-pr`: the `cd <root checkout>` line above.
- This repo's `AGENTS.md`: `install.sh` "copies, updates and checks" the files.

## Tests

Per `AGENTS.md` § Testing, one table-driven test per rule. New `agent-team/scripts/test_install.py`, skipped outside collective-wisdom like `test_root_links.py`. It builds a throwaway collective-wisdom repo in a temp folder (this repo's `install.sh` plus a small `agent-team/` tree, two commits, a bare `origin`), and a throwaway app repo.

- Install and update cases, one table: fresh install at `--to <first>`; update to `<second>` reports the commit list, the `update`/`add` lines and a deletion TODO for a file the second commit dropped; update with a hand-edited skill refuses and lists it; the same with `--force` overwrites; update with no `installed-from.txt` refuses; `--to` a commit not on `origin/main` refuses; `--dry-run` writes nothing. Each case checks the exit code, the pin line and the files.
- Drift check cases, one table: clean app (exit 0), one changed and one missing file (exit 1, both listed), an extra app-owned skill (not reported), a SHA unknown to the clone (exit 2).
- Root finding: `test_symlinked_root.py` keeps its link-layout cases and gains rows that run each root lookup with the scripts sitting outside the app (cwd in the app, from its top and from a subfolder) and from a git worktree of the app. Each must name that repo's `project.md` and `.agent-team/state.json`.

`test_root_links.py` doesn't change, and must keep passing.

## Calls I made

- **`--update` without `--to` fetches and moves to `origin/main`**, so you don't have to pull this clone first. A plain install still uses this clone's `HEAD`.
- **Pins must be on `origin/main`.** An app can't be pinned to an unmerged branch, even by hand with `--to`.
- **Files come from `git archive` of the pinned commit**, so this clone no longer has to be clean. That refusal goes away; the pin is exact by construction.
- **An update refuses when the app's copies drifted from the old pin**, and lists the files. `--force` overwrites them. The other choice, overwriting with a warning, loses edits that nobody noticed.
- **The drift check lives in `install.sh` and needs a clone of this repo** that has the pinned commit. An in-app check (a hash manifest or a script the app's CI runs) was left out; it can be its own ticket.
- **Files dropped upstream show as deletion TODOs, never deleted**, as the installer does for old skill copies today.
- **Seeded files and `settings.json` are not drift-checked**, because the app owns them after seeding.
- **`merge_pr.py` now runs from the root checkout (`cd <root checkout> && python3 scripts/merge_pr.py`)**, because scripts find the repo from the current directory.
- **`installed-from.txt` keeps its one-line format**, so nothing that reads it changes.
- **The spec file was renamed** from `...-agent-team-plugin-design.md` to `...-install-update-design.md`. The branch keeps its `feat/cw-42-agent-team-plugin` name to avoid re-pushing.

## Risks

- `git archive` respects `export-ignore` in `.gitattributes`. This repo has no `.gitattributes`; adding one with `export-ignore` under `agent-team/` would silently drop files from installs.
- A script run from outside any git repo now falls back to the current folder instead of its own parent. Every documented call runs from the repo top, so none changes.
