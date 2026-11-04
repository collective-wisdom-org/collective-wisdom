# As-built: Chief of Staff for collective-wisdom itself

**Shipped:** in PR #10
**Ticket:** CW-9 (#9)
**Spec:** [2026-11-03-repo-chief-of-staff-design.md](../specs/2026-11-03-repo-chief-of-staff-design.md)
**Plan:** [2026-11-03-repo-chief-of-staff.md](../plans/2026-11-03-repo-chief-of-staff.md)

## What shipped

- Root symlinks into `agent-team/`: `.claude/skills`, `.claude/agents`, `.claude/settings.json`, `.agents/skills`, `scripts`, `docs/superpowers/README.md`, and one link per entry in `agent-team/docs/agents/`. A real root `docs/agents/project.md` (GitHub Issues, prefix `CW`), `AGENTS.md`, `CLAUDE.md`, and a README section on running the Chief of Staff here.
- Scripts keep the invoked root through a symlinked `scripts/`: `.absolute()` instead of `.resolve()` in the root lookups, `sys.path` inserts in `cos_rank.py`, `DEFAULT_STATE` in `cos_idle_check.py` and `cos_parent_check.py`. `cos_rotation_check.skill_paths()` resolves skill paths through links, and `skill_commit` uses `:(top)` pathspecs.
- Agent files for `implementer`, `code-reviewer` and `security-reviewer`, with role docs `implementer.md` and `code-review.md` and a subagent section in `security-review.md`. `build-from-plan`, `open-pr` and `security-review` start them by `subagent_type` with the documenter-style fallback. `org-chart.md` says why thread roles and the project manager pass have no agent file.
- Tests: `test_symlinked_root.py`, `test_root_links.py` (skips in apps), `test_agent_files.py` (skips in apps), and rotation tests in `test_cos_rotation_check.py`.

## Differs from the spec

- `agent_usage.py` also changed to `.absolute()` (its test needs it); `cos_brief.py` needed the same change and `cos_rank.py` a `sys.path` insert, which the spec had marked "check".
- No registry tests for the agent set or their models: they would fail apps with their own agents.
- `.gitignore` also ignores `.superpowers/`.

## Verification

- `python3 -I -m pytest -q agent-team/scripts`: 271 passed.
- `scripts/cos_brief.py --help` and `scripts/cos_rank.py --help` run from the root.
- `install.sh --dry-run` into a fresh repo seeds only the template `project.md` and adds the new agent files and role docs.

## Not verified

- No Chief of Staff thread has run from this root yet. The first live run is the real test of the GitHub tracker adapter here.
