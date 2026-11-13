# CW-282 plan: install the agent-gantt plugin from install.sh

**Spec:** `docs/superpowers/specs/2026-11-13-cw-282-install-agent-gantt-design.md`. The spec is the source for every behavior; this plan only orders the work and sets the checks.

Test command: `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest` if pytest is missing). This ticket touches neither `mods/` nor `agent-team/scripts/dashboard/`, so the Node tests do not run.

## Task 1: The install step

- `install.sh`, `machine_install`: after the Cursor hooks step and before the instruction-block loop, add the agent-gantt step. No `claude` on PATH adds a to-do with the manual command. Otherwise `claude plugin list --json` is checked with `python3 -I` for the id `agent-gantt@collective-wisdom`. Not found: a dry run prints the `install  agent-gantt plugin` line and counts one change; a real run runs `claude plugin install ... --scope user`, prints the line and counts one change on exit 0, and adds a to-do with the last output line on any other exit.
- Check: `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Task 2: Tests

- `agent-team/scripts/test_install_machine.py`: `install()` puts a stub-bin folder first on PATH and shadows any real `claude`. The stub reports the plugin installed by default, so the existing tests keep their assertions. A `claude=` keyword picks `installed`, `missing`, `ok` or `fail`.
- One table-driven test, `test_agent_gantt_plugin_install`, with five rows: no claude, already installed, install works, install fails, dry run. Each checks the exit code, whether `plugin install` ran, the `Done: N change(s)` count and the to-do or dry-run line.
- Check: `python3 -I -m pytest -q agent-team/scripts/test_install_machine.py`.

## Task 3: Docs

- `README.md` § Agent pane: `./install.sh` installs the plugin at user scope when `claude` is on PATH and lists it under `TODO:` otherwise; the three manual routes are for the desktop app and for a machine where `install.sh` skipped it or failed.
- `AGENTS.md` § Product and the mod bullet: `install.sh` installs the mod with `claude plugin install`.
- `docs/agents/project.md` § Security overlays: add `~/.claude/plugins` to the paths `install.sh` writes.
- Check: no doc still says `install.sh` does not install the mod (`grep -rn "does not install" README.md AGENTS.md docs/agents/project.md`).

## Final check

`shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` and `python3 -I -m pytest -q agent-team/scripts`.
