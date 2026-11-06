# CW-133 plan: detect untracked in-flight tickets

Spec: `docs/superpowers/specs/2026-11-05-cw-133-detect-untracked-tickets-design.md` (approved at 1676f16). Edit under `agent-team/` only.

## Task 1: script, sweep part and tests (code)

- `agent-team/scripts/cos_untracked_check.py`, modelled on `cos_ready_check.py` (reuse its `load_state`, `gh`, `json_values`, `branch_prefix`, `BRANCH`, `fail`; extend `load_state` use to `merged`). Options `--file --open-prs --issues --login`. Trusted logins: `--login` or `cos_brief.own_login()` (once, any failure or empty is `fail`), plus `project_config.value("Owner login")` if set, lowercase compare. GitHub tracker: issue author must be trusted. Linear/Jira: PR author must be trusted. Output and exit codes exactly as the spec's Change section.
- `cos_sweep.py`: fourth part `untracked` through `part()`, args `--issues`, `--login`; last line `; untracked: CW-125 #132, CW-126` before `; didn't run:`; untracked counts toward exit 1. Update the docstring.
- Tests per AGENTS.md § Testing: `test_cos_untracked_check.py` (one table-driven test plus a Linear/author row and login-unreadable row) and new rows in `test_cos_sweep.py`; existing sweep rows pass `--issues` empty and `--login`. Test lines must not exceed feature lines.
- Verify: `cd agent-team/scripts && python3 -m pytest -q`.

## Task 2: skill docs (markdown)

Per the spec: `chief-of-staff/SKILL.md` (§ Sweep, § Commands `adopt N`, new § Adopt, § Tools, the sweep sentence in the Tools list), `rotation.md`, `startup.md`, `status.md`. Say in the docs that only own-login or Owner-login tickets are listed.
