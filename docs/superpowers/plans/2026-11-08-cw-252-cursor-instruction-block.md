# CW-252 plan: Cursor rule file for the instruction block

Spec: `docs/superpowers/specs/2026-11-08-cw-252-cursor-instruction-block-design.md` (approved).

1. `install.sh`: add a `rule` mode to `mpython` that writes the whole file `~/.cursor/rules/collective-wisdom.mdc` (front matter `description`, `alwaysApply: true`, blank line, template text). Status words `created`, `updated`, `present`, `invalid` (folder or non-UTF-8 file). Use the existing `write()`. Call it in `machine_install` after the CLAUDE.md/AGENTS.md loop; add the `Fix ~/.cursor/rules/collective-wisdom.mdc by hand` TODO on `invalid`; delete the Cursor paste TODO.
2. `test_install_machine.py`: extend the fresh-install test (file content, no paste TODO) and add one table-driven test (stale file replaced, folder at the path gives the fix TODO while the rest installs, rerun is `present`).
3. Docs: `docs/agents/project.md` § Security overlays path list, `README.md` install lines, `docs/compatibility.md` Cursor Install cell, install note and G1 (stay `partial`; Cursor-thread quote is not proven).
4. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh`.
