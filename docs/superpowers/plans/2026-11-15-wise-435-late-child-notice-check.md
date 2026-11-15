# WISE-435 plan: late child notice check

Spec: `docs/superpowers/specs/2026-11-15-wise-435-late-child-notice-check-design.md` (approved).

1. `agent-team/scripts/cos_idle_check.py`: add `late_children(state, db, now=None)` per the spec § The check. Reuse `store_rows`, `parse_ts`, `clock12`/`hhmm`, `wait_read_from_store` + `check_wait` (exit 0 means skip). Return a list of `"<ticket> <status|question> <h:mm am/pm> UTC"`. Never raise: any store error, missing table or DB returns `[]`. Runs table has `ordinal`, `status`, `completed_at`; requests table `orchestration_v2_projection_runtime_requests` has `thread_id`, `status`, `created_at`. Update docstring.
2. `agent-team/scripts/cos_rotation_check.py` `run_hook`: after the rotation line, skip when state `paused`, `reset` or `takeover` set; else call `late_children` (load via `load_module("cos_idle_check")`, db from `COS_T3_DB` env override else default) and append `late-child: <entries joined "; ">; read each per chief-of-staff SKILL.md § Child path`. Reason = rotation reason + "; " + late line when both. Works for Claude (`decision: block`) and Cursor (`followup_message`). Plain mode unchanged. Update docstring.
3. One table-driven test in `test_cos_rotation_check.py` per the spec § Test (fake store, reuse `run_hook` helper).
4. Docs: `chief-of-staff/rotation.md` § Thread rotation, `chief-of-staff/SKILL.md` § Turn start.
5. Verify: `python3 -I -m pytest -q agent-team/scripts`.
