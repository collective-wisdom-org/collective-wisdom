# CW-253: Cursor rotation hook, plan

**Spec:** [spec](../specs/2026-11-08-cw-253-cursor-rotation-hook-design.md)

Test command: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Tasks

1. `agent-team/scripts/cos_rotation_check.py`: the `--hook` payload table, optional context size in `check` and `decide`, the Cursor transcript lookup in plain mode, `$CURSOR_PROJECT_DIR` in `_root()`. Spec §§ 1 to 3. Tests: one table for the hook payloads, one case for plain mode on Cursor, in `test_cos_rotation_check.py`.
2. `install.sh`: `cursor-hook` mode in `mpython`, the `~/.cursor/hooks.json` call and its TODO. Spec § 4. Tests: one table over starting states in `test_install_machine.py`, each run twice.
3. Docs (spec § 5): `docs/agents/project.md` Security overlays, `docs/compatibility.md`, `README.md`, `agent-team/.claude/skills/chief-of-staff/rotation.md` and `state-keys.md`.
