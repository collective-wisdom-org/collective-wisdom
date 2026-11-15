# CW-339 plan: update the agent-gantt plugin

Spec: `docs/superpowers/specs/2026-11-14-cw-339-update-agent-gantt-plugin-design.md` (approved; the spec's Design section is the contract, including every output line). Tests follow `AGENTS.md` § Testing: table-driven, test lines not above feature lines.

## Task 1: the script, `install.sh`, README

Files: `agent-team/scripts/gantt_plugin.py` (new), `agent-team/scripts/test_gantt_plugin.py` (new), `install.sh`, `agent-team/scripts/test_install_machine.py`, `README.md`.

1. Write `gantt_plugin.py` per spec Design 1 (output table, version compare, `--dry-run`, 120 s timeout, always exit 0). Run with `python3 -I`; stdlib only. Find the clone from `__file__`; honour no env override except what the test needs (the test puts a stub `claude` first on PATH and copies the script into a temp clone).
2. `test_gantt_plugin.py`: one table per spec Tests bullet 1.
3. `install.sh`: replace the inline list check with a call to the script per Design 2; keep the no-`claude` and install paths; the restart line goes after `Done:` and before `TODO:`. `shellcheck install.sh` must pass.
4. `test_install_machine.py`: the `world` fixture copies `gantt_plugin.py` and writes `mods/agent-gantt/.claude-plugin/plugin.json` (0.1.12); stub gets an installed-version knob and a `plugin update` branch; add the two rows from spec Tests bullet 2.
5. README per spec Design 4 (Agent pane, install paragraph, two TODO bullets).

Verify: `python3 -I -m pytest -q agent-team/scripts/test_gantt_plugin.py agent-team/scripts/test_install_machine.py`, `shellcheck install.sh`. Commit `feat: update the agent-gantt plugin in install.sh (CW-339)`.

## Task 2: the running Chief of Staff

Files: `agent-team/scripts/cos_state.py`, `agent-team/scripts/cos_rotation_check.py`, their tests, `agent-team/.claude/skills/chief-of-staff/rotation.md`, `.../state-keys.md`.

1. `cos_state.py`: allow top key `ganttPluginVersion` (dotted-integer string or null), rejecting others like `skillCommit` does.
2. `cos_rotation_check.py`: read the clone's mod version (file read only, never run `claude`), add the plugin-change trigger per Design 3 (quiet-turn rule shared with the skill change, skill change wins the line, off on null/unreadable, no effect on mode `none`, merge target branch only); update the docstring.
3. Tests per spec Tests bullets 3 and 4.
4. Docs per Design 3: `rotation.md` (trigger-table Plugin change row; Reset step running `gantt_plugin.py` first with a Cleanup line on `todo`; take over step 1 runs it and step 4 saves `ganttPluginVersion`, incl. resume mode), `state-keys.md` bullet.

Verify: `python3 -I -m pytest -q agent-team/scripts`. Commit `feat: reset the Chief of Staff to load an updated agent-gantt plugin (CW-339)`.

## Task 3: check on this machine

Run `gantt_plugin.py --dry-run` against the real `claude`; report the line. Note whether a fresh-context reset loads an updated plugin cannot be checked here (goes to the PR's Not proven).
