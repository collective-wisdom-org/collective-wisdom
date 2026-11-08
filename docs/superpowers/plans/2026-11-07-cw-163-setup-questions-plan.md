# CW-163 plan: ask setup questions before the Chief of Staff starts in a new repo

Spec: [design](../specs/2026-11-06-cw-163-setup-questions-design.md). Shared files are edited under `agent-team/`; `README.md` sits at the root and `docs/agents/project.md` is this repo's own and stays as it is. The spec's section numbers are used below.

## Tasks

Two write scopes, disjoint, so they run in parallel.

### A. Scripts and tests (scope: `agent-team/scripts/`, `agent-team/templates/project.md`)

1. `setup_repo.py` (spec §§ 2, 3, 4): the `status`, `user` and `write` commands. `status` prints `missing`, `set` or `placeholders: <rows>`, then one JSON line of facts (`host`, `repo`, `repo_key`, `target`, `gh_logins`, `mapped_login`, `user_md_exists`, `pinned`, `has_workflows`, `test_guess`, `prefix_guess`, `product_guess`), and writes nothing. `user` writes this repo's row in `user.md`, creating the file from `templates/user.md` when missing. `write` renders or updates `docs/agents/project.md` and the `.agent-team/` line in `.gitignore` inside a worktree, and refuses a directory that is not a worktree of the repo or is on the merge target.
2. `agent-team/templates/project.md`: only what the render needs (spec § 3, the rows written with no question).
3. `test_setup_repo.py` (spec § Testing): table-driven, `HOME` pointed at a temp folder. Test lines do not exceed feature lines.

### B. Prose and docs (scope: `agent-team/.claude/skills/chief-of-staff/`, `agent-team/templates/machine-instruction.md`, `agent-team/docs/agents/chief-of-staff.md`, `README.md`)

1. New `chief-of-staff/setup.md` (spec §§ 1, 3, 5, 6): the status check, the questions, the PR walk-through and the endings.
2. `startup.md` § Setup step 0, and the `set up this repo` command, trigger and reference-file rows in `SKILL.md`.
3. `machine-instruction.md`: the one exception for the setup command.
4. `README.md` Adopt in a repo, and a bullet in the Chief of Staff role doc. Plain sentences, no em dashes.

## Verify

```
python3 -I -m pytest -q agent-team/scripts
shellcheck install.sh tag-release.sh agent-team/scripts/*.sh
```
