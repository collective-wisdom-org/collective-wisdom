# CW-206 plan: conflict at MERGE READY goes to the merge lane

Spec: `docs/superpowers/specs/2026-11-08-cw-206-conflict-merge-lane-design.md`. Test command: `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: `noApproval` state key (`agent-team/scripts/cos_state.py`)

- Add `noApproval` to `TICKET`. `check(t)` rejects it unless `true` or `None`, and rejects `true` outside `merge`, `merge-queued`, `blocked`.
- `op_stage`: when the new stage is not one of those three, pop `noApproval` (before `check`).
- Document it in the module docstring and in `chief-of-staff/state-keys.md` § State keys.
- Test (`test_cos_state.py`, one table): accepted in the three stages, rejected elsewhere and for other values, dropped by a stage op to `awaiting-merge`.

## Task 2: `conflict-stand` caller (`agent-team/scripts/cos_route.py`)

- `ROUTES["conflict-stand"] = {"awaiting-review": "merge", "awaiting-merge": "merge"}`; `lane_for` returns None when the setting is not `off` (same as `conflict-keep`).
- The stage op (send and queue) gets `"set": {"noApproval": true}` for this caller.
- Update the docstring table. Test rows in `test_cos_route.py`: send merge with `off` and the set; `no` with `on`; queue with the set when the merge slot is busy.

## Task 3: `conflict stand` last line (`agent-team/scripts/cos_head_check.py`)

- `check()` gets a `no_approval` that is true for `--no-approval` or the ticket's `noApproval` in state (read in `read_ticket`). `off` + no approval + conflicting, head unchanged: plain `CONFLICT` relay and `head-check: conflict stand`. Other branches unchanged.
- Update the docstring (four lines, what `--no-approval` and `noApproval` do). Test rows in `test_cos_head_check.py`: the `off` + `--no-approval` row becomes `conflict stand`; `on` + `--no-approval` stays `conflict withdraw`; `off` + `noApproval` in state and no flag gives `conflict stand`.

## Task 4: Chief of Staff text (`agent-team/.claude/skills/chief-of-staff/`)

- `approvals.md` step 1, `SKILL.md` § Send or queue (caller list, head check list), `SKILL.md` § Child path `BLOCKED:` bullet, `review.md` § approve N on awaiting-review, as spec Builds item 4 says. Keep the wording short; no em dashes.
