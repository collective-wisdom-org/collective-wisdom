# CW-42: Pin, update and drift-check the agent team in apps: Implementation Plan

**Spec:** [2026-11-03-cw-42-install-update-design.md](../specs/2026-11-03-cw-42-install-update-design.md)
**Ticket:** [CW-42](https://github.com/dbeallor/collective-wisdom/issues/42)

Edit shared files under `agent-team/`, never through the root links. Run `python3 -I -m pytest -q agent-team/scripts` (or `uvx pytest -q agent-team/scripts`) and `shellcheck install.sh agent-team/scripts/*.sh` after each task. Test lines should not exceed feature lines (AGENTS.md § Testing).

## Task 0: tests first

- Add rows to `agent-team/scripts/test_symlinked_root.py` that run each root lookup (`project_config.DEFAULT`, `cos_state.DEFAULT_FILE`, `cos_idle_check.DEFAULT_STATE`, `cos_parent_check.DEFAULT_STATE`, `docs_index.INDEX`, `release_notes.NOTES`, and the `ROOT` of `merge_pr`, `pr_diff_delta`, `cos_merged_check`, `cos_ready_check`, `cos_rotation_check`) with the scripts folder **outside** the app (a real copy elsewhere in `tmp_path`, no symlink), cwd in the app top, then cwd in an app subfolder, then cwd in a `git worktree` of the app. Each must name that repo's path. The app needs `git init` for these rows.
- Create `agent-team/scripts/test_install.py` (skip outside collective-wisdom: `(TOP / "install.sh").exists()`), per the spec's Tests section: a throwaway collective-wisdom repo (copy of `install.sh`, a small `agent-team/` tree with `.claude/skills/x/SKILL.md`, `.claude/agents/`, `.claude/settings.json`, `scripts/a.py`, `docs/agents/a.md`, `docs/superpowers/README.md`, `templates/{project.md,AGENTS.md,gitignore}`; two commits; a bare `origin` it pushes `main` to), plus a throwaway app repo. Two table-driven tests: install/update cases and drift-check cases, exactly the cases listed in the spec. Each case checks exit code, last line, the pin line and files.
- Run them; they must fail for the right reason before Tasks 1 and 2.

## Task 1: scripts find the app from the working repo

- New `agent-team/scripts/app_root.py`: `root()` returns `Path(git rev-parse --show-toplevel)` run in the current directory, else `Path.cwd()`. Resolve symlinks no further than git does.
- Replace every `Path(__file__).absolute().parent.parent` root in: `project_config.py` (`DEFAULT`), `cos_state.py` (`DEFAULT_FILE`), `cos_idle_check.py`, `cos_parent_check.py` (`DEFAULT_STATE`), `cos_rotation_check.py` (`ROOT`, drop `HERE.parent`), `cos_handoff.py`, `cos_ready_check.py`, `cos_merged_check.py`, `cos_sweep.py`, `cos_worktree_check.py`, `merge_pr.py`, `pr_diff_delta.py` (`ROOT`), `docs_index.py` (`INDEX`), `release_notes.py` (`NOTES`), and `agent_usage.project_name`. Keep `sys.path.insert(0, ...parent)` lines and the `PROJECT_MD` / `COS_STATE_FILE` overrides. Where a script built `gh.sh` from `ROOT / "scripts"`, use `Path(__file__).absolute().parent / "gh.sh"` instead (`merge_pr.py`, `cos_ready_check.py`, `cos_merged_check.py` and the like).
- `wait-for-ci.sh`: `cd "$(git rev-parse --show-toplevel)"` instead of `cd "$(dirname "$0")/.."`, and call `gh.sh` as `"$(dirname "$0")/gh.sh"` (resolve `dirname` to an absolute path first).
- `merge-pr` skill (`agent-team/.claude/skills/merge-pr/SKILL.md`): the root-checkout line becomes `cd <root checkout> && python3 scripts/merge_pr.py <N> <approved head SHA>`.
- Existing tests must still pass, including `test_root_links.py` and the `test_script_runs_by_link_path` rows.

## Task 2: `install.sh` modes

Rewrite `install.sh` (keep it bash, shellcheck-clean). Spec § 1 to § 4.

- Flags: `--dry-run`, `--to <ref>`, `--update`, `--force`, `--check`. `--check` and `--update` are exclusive. `--check` takes no `--to` or `--force`.
- Resolve the target SHA: `--to <ref>` via `git rev-parse --verify <ref>^{commit}`; install default is `HEAD`; update default runs `git fetch origin` then `origin/main`. Refuse (exit 1) unless `git merge-base --is-ancestor <sha> origin/main`. Keep the checks that this clone is its own repo root and that the target is a git repo with no uncommitted changes in `TOUCHED`. Drop the clean-clone check.
- Extract `git archive <sha> agent-team | tar -x -C <tmp>` and set `SRC` to `<tmp>/agent-team`; clean the temp dir on exit. The copy rules (`sync_dir`, `seed_file`, settings handling, `.agents/skills` link, `.gitignore` lines, old-copy warning) stay as they are.
- `installed-from.txt`: parse with a strict regex `^collective-wisdom [0-9a-f]{40}$`; anything else is exit 2 for `--check` and `--update`.
- Shipped set: files under `.claude/skills`, `.claude/agents`, `scripts`, `docs/agents` of an extracted commit, mapped to app paths (same mapping `sync_dir` uses; skip `__pycache__`, `.pyc`, `.DS_Store`).
- `--check`: extract the pinned SHA (`git cat-file -e` first; exit 2 with "git fetch" advice if missing), compare each shipped file with the app copy, print `changed  <path>` / `missing  <path>`, last line `check: matches collective-wisdom <sha>` (exit 0) or `check: drift in N file(s) against collective-wisdom <sha>` (exit 1). Writes nothing.
- `--update`: require the pin file; run the drift check against the old pin and refuse on drift (list files, exit 1) unless `--force`; run the normal copy at the new SHA; print `collective-wisdom <old12> -> <new12> (N commits)`, `git log --oneline <old>..<new> -- agent-team`, the usual `add`/`update` lines, and a TODO `Delete <path>: collective-wisdom no longer ships it ...` for each path in old shipped set but not new. Never delete. Same SHA and no drift: print `already at <sha>, nothing to do` and exit 0.
- `--dry-run` writes nothing in every mode.
- Never run or write outside the paths the user gave (security overlay): quote every expansion, use `--` before paths, no `eval`.

## Task 3: docs

- `README.md`: § Install and § Update describe the three modes, `--to`, `--force`, the update report and deletion TODOs; § Layout lines unchanged. Prose follows `human-writing`: plain sentences, no em dashes.
- `agent-team/.claude/skills/ship-loop/SKILL.md` § Team mode, Workflow files: "followed by an install PR in the app that runs `install.sh --update` and so bumps `docs/agents/installed-from.txt`".
- `AGENTS.md`: `install.sh` "copies, updates and checks".
- No spec, as-built, index or release-note changes here; closeout docs come right after the PR opens (open-pr § Closeout docs).

## Final verification

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` both green; `./install.sh --dry-run <temp app>` and `--check` by hand against a temp app, outputs pasted in the PR.
