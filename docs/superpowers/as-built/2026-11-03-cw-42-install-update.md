# As-built: Pin, update and drift-check the agent team in apps

**Shipped:** in PR #47
**Ticket:** CW-42 (#42)
**Spec:** [2026-11-03-cw-42-install-update-design.md](../specs/2026-11-03-cw-42-install-update-design.md)

## What shipped

- `install.sh` gained `--to <ref>`, `--update`, `--force` and `--check`. Files are copied from `git archive` of the target commit, which must be on `origin/main`; the clone no longer has to be clean. `--update` fetches `origin/main` when `--to` is absent, refuses when the app's copies drifted from the old pin (unless `--force`), and reports the commit range, the added and updated files, and a deletion TODO per file the new commit no longer ships. `--check` lists changed and missing files against the pinned commit.
- `agent-team/scripts/app_root.py`: `root()` is `git rev-parse --show-toplevel` in the current directory, else the current directory. Every script that built its root from `__file__` uses it. `gh.sh` is found next to each script. `wait-for-ci.sh` changes into the git top level.
- The `merge-pr` skill runs `cd <root checkout> && python3 scripts/merge_pr.py ...`. `README.md`, `AGENTS.md` and the ship-loop workflow-files rule describe the new modes.
- Tests: new `test_install.py` (install and update table, drift check table) and a root-finding test in `test_symlinked_root.py` that runs the scripts from outside the app, from a subfolder and from a worktree.

## Differs from the spec

- A deletion TODO is only listed when the file still exists in the app.
- `--force` without `--update`, and `--check` with `--update`, `--to` or `--force`, are usage errors (exit 2). A `--to` ref that starts with `-` is rejected.
- `--update` with no `installed-from.txt` exits 1 (a refusal); a malformed pin or a SHA the clone lacks exits 2.
- A plain install with no `--to` refuses when this clone's `HEAD` is not on `origin/main`.
- `agent_usage.project_name` takes the repo directory (default `app_root.root()`) instead of a script path.
- `cos_rotation_check.py --hook` roots at `CLAUDE_PROJECT_DIR` when set, because the Stop hook's working directory can drift away from the repo top. Other modes use the current repo.
- `--check` exits 2 when it cannot extract the pinned commit.

## Verification

`uvx pytest -q agent-team/scripts` passes (454 tests) and `shellcheck install.sh agent-team/scripts/*.sh` is clean. `--dry-run`, `--check` and `--update` were run by hand against a throwaway clone and app.
