# Continuation children for restarts, answers, resumes and rate-limit continues (CW-14) implementation plan

Spec: `docs/superpowers/specs/2026-11-03-cw-14-continuation-children-design.md` (approved at 9c74a77). Edit only under `agent-team/` (plus the docs under `docs/superpowers/`). Test command: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh agent-team/scripts/*.sh`.

Conventions to match: `Path(__file__).absolute()` for paths, `project_config` for prefix and branch head, `fail()` printing `cos_<name>: <what>` and exiting 2, subprocess calls with `timeout=30`, tests load the module with `importlib.util` and a `run()` helper like `test_cos_handoff.py`, fixture project is prefix `ABC`.

## Task 1: `cos_worktree_check.py`

Files: `agent-team/scripts/cos_worktree_check.py` (new), `agent-team/scripts/test_cos_worktree_check.py` (new).

- Spec § 1. `<PREFIX>-N <worktree path> [--file STATE] [--root DIR]`. Checks in order: ticket and `branch` from state (branch pattern as `cos_handoff.rejected`; import it or the pattern, don't copy), path is in `git -C <root> worktree list --porcelain` (resolved), HEAD is the branch, `status --porcelain --untracked-files=all` empty (with `--no-optional-locks`), `ls-remote origin refs/heads/<branch>` sha equals local `rev-parse HEAD`.
- Output lines and exit codes exactly as the spec. Print values only after a pattern check. Never run a git command that writes; never fetch.
- Test: one table over real git repos in `tmp_path` (bare origin, root clone, one added worktree on the ticket branch, pushed). Rows per spec § 3.

## Task 2: skill prose (no tests)

Files: `agent-team/.claude/skills/chief-of-staff/SKILL.md`, `agent-team/docs/agents/chief-of-staff.md` (script list).

- Spec § 2, only the sections it names: Tools Bash bullet, § Full pass step 3 restart bullet, § Send or queue ("Continuation child", the "keeps its child" paragraph, the T3 notice paragraph, the template's stage line). No other section.
- Prose follows `human-writing`: plain sentences, no em dashes.

## Task 3: check installs and links

- Check whether `install.sh`, `test_agent_files.py` or `test_root_links.py` list scripts by name; add the new one only if they do. Run the full suite and shellcheck.
