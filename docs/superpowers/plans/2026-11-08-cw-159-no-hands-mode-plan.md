# CW-159 plan: No Hands mode

Spec: `docs/superpowers/specs/2026-11-08-cw-159-no-hands-mode-design.md` (approved at ba1aa02). The spec's Builds list is the task list; this plan orders it. Tests per `AGENTS.md` § Testing: one table-driven test per rule, test lines no more than feature lines. Run `python3 -I -m pytest -q agent-team/scripts` after each task. Edit files under `agent-team/`; never touch `agent-team/` copies of `docs/agents/project.md`.

## Task 1: setting, state key, `no_hands.py`

- `agent-team/scripts/project_config.py`: `no_hands_setting()` reads the three rows (spec Builds 1) with the same committed-read helper as `approval_setting`; anything missing or bad is off. Add the rows to `docs/agents/project.md` and `agent-team/templates/project.md` (`off`, `10`, `200`); check `setup_repo.py`/`install.sh` seeding and `test_setup_repo.py` still pass.
- `agent-team/scripts/cos_state.py`: top-level key `noHands`, shape check, a `no-hands` op (write run record), and the `start` op appends the ticket to `noHands.started` while a run is active.
- New `agent-team/scripts/no_hands.py`: `start`, `check`, `drain`, `end`, `active()` (spec "no_hands.py"). Reuse `cos_user_check.py` for `latest` (start) and `item` (re-verify). Cost via `agent_usage.py --ticket`.
- Tests: `test_project_config.py` row, `test_no_hands.py`, `test_cos_state.py` row for `noHands`.

## Task 2: approval scripts

- `approval_policy.py`: `HANDS_PATH`, `on_hands_path()`, `decide`/`cmd_auto` auto for every level while `no_hands.active()`, `check no-hands`.
- `cos_approve_pr.py`: under an active run `auto_gate` skips the tolerance and uses the hands path in place of the approval path; rename, file cap, flag, migration and conflict-note stops stay.
- Hands-path import test (every local import of a hands-path script is on the list).
- Tests per spec Builds 6 for `test_approval_policy.py` and `test_cos_approve_pr.py`; the existing tests pass unchanged.

## Task 3: slot fill

- `cos_tick.py`: `run … no_hands.py check` line while a run is active; no `start-todo` on `drain`/`stop`, with `report (filling stopped: No Hands <reason>)`. One `test_cos_tick.py` row.

## Task 4: skill and role text

Per spec Builds 5: new `chief-of-staff/no-hands.md`; edits to `SKILL.md` (reference table, Commands, child task template CI line, report format line), `approvals.md`, `kill-switch.md`, `state-keys.md`, `project-manager/SKILL.md` § Backlog pick, `ship-loop/SKILL.md` § Approvals, `docs/agents/chief-of-staff.md`, `docs/agents/org-chart.md`. Keep wording short; no em dashes. `test_agent_files.py`, `test_call_sites.py` and `test_section_pointers.py` must pass.

## Closeout

`**Shipped:**` line in the spec and the release note are done in open-pr § Closeout docs. Compaction pass after Task 4.
