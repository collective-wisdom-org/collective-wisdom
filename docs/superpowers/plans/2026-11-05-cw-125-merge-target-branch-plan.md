# CW-125 plan: merge target branch setting

Spec: `docs/superpowers/specs/2026-11-05-cw-125-merge-target-branch-design.md`. Edit under `agent-team/`, never through the root links. Do not touch `install.sh`, `tag-release.sh` or `agent-team-update.sh`.

## Task 1: project_config

- Add `target_branch()` to `agent-team/scripts/project_config.py`: `value("Merge target branch")`, default `main`; invalid names `SystemExit("project.md: 'Merge target branch' row ...")`. Valid: `[A-Za-z0-9._/-]+`, no leading `-`, `/` or `.`, no trailing `/`, `.` or `.lock`, no `..` or `//`.
- `approval_setting()`: fetch `origin <target>`, show `refs/remotes/origin/<target>:docs/agents/project.md`. Guards, each giving `("strict", why)`: target starts with `branch_head()`; the committed file's target (parsed with `value` over `_parse(text)`, same validation, default `main`) differs from the working tree's target.
- Test: `target_branch()` table and extra `approval_setting` rows in `test_project_config.py`.

## Task 2: scripts

Replace each app-side `main` with `target_branch()` (see spec § Scripts): `merge_pr.py`, `pr_diff_delta.py`, `review_scope.py`, `release_notes.py`, `cos_approve_pr.py`, `cos_brief.py`, `cos_rotation_check.py`. Fetch refspec `+refs/heads/<t>:refs/remotes/origin/<t>`. Update messages and docstrings. Existing tests must pass unchanged with no row. Add one table-driven `gate()` test in `test_merge_pr.py` (row `dev`: base `dev` ok, base `main` refused, root on `main` refused; no row: today's behavior). Use `PROJECT_MD` to set the row.

## Task 3: project.md rows, skills, docs

- Add the `Merge target branch` row to `agent-team/templates/project.md` § Git and GitHub and to `docs/agents/project.md` (value `main` there). Template Repo invariants say "the merge target branch".
- Swap `main` for "the merge target branch" in the skills and role docs where it means the PR base (spec § Skills and docs). Leave collective-wisdom's own `main`, the `release-notes` branch exception, and installer text alone. `ship-loop` head-moved note: `by merging <target>`.

## Verify

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`; `grep -nw main agent-team/scripts/*.py` outside tests shows only the default and non-branch text.
