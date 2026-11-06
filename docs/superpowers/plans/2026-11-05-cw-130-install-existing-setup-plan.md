# CW-130 plan: fit install.sh to repos with their own agent setup

Spec: [2026-11-05-cw-130-install-existing-setup-design.md](../specs/2026-11-05-cw-130-install-existing-setup-design.md). Paths are at the repo root unless noted. Read the spec first; it has the rules and the exact TODO texts.

1. `install.sh`: after the `settings.json` block, replace its single TODO with the spec's rule (no TODO when the file contains `cos_rotation_check.py`; otherwise the hook TODO followed by the shipped `settings.json`, indented). Add the `AGENTS.md` heading check (only when the file existed before this run, i.e. was not just seeded) and the `.agents/skills` check (directory, file or link to anything but `../.claude/skills`). Checks run in dry runs too and never write. In a dry run `AGENTS.md` may not exist yet, so key "existing" off a path test done before `seed_file`.
2. `agent-team/scripts/test_install.py`: change the fixture's shipped `settings.json` to JSON containing the hook command and `templates/AGENTS.md` to the four headings. Check the existing tests still pass. Add one table-driven `test_existing_setup` per the spec § Tests (six rows, TODO substrings present and absent, planted files unchanged).
3. `README.md`: add `## Adopt in a repo` after `## Requirements` (the nine steps in the spec), and adjust § Install's "never overwrites" sentence and § Update's last sentence about the hook.
4. Verify: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
5. Open the PR, closeout docs, docs check, code review, security review, per `ship-loop`.
