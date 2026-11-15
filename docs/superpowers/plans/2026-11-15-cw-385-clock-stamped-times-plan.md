# CW-385 plan: clock-stamped status and comment times

Spec: [design](../specs/2026-11-15-cw-385-clock-stamped-times-design.md)

## Tasks

1. `agent-team/scripts/cos_state.py`
   - `stamp_text(iso)`: `YYYY-MM-DD h:mm am|pm UTC` via `clock12`.
   - `fill_status(text, stage_at)`: replace `{since}` with `stamp_text(stage_at)`; reject `since` + digit before the first `"`.
   - `op_start`, `op_stage`: fill the status after `stageAt` is settled. `op_set`: when `set` has `status`, fill it with the ticket's `stageAt`.
   - `merge_set`: a `heldApproval` dict that names `at` is rejected; one without gets `at = now()`. `check()` still requires `at`.
   - `now` subcommand (`--iso` for the ISO form); no state file read. Update the module docstring.
2. `agent-team/scripts/test_cos_state.py`
   - One table-driven test: for start, stage change, same-stage stage op, set of status: saved status contains `stamp_text(stageAt)`. Rows: hand-typed `since 5:20am` rejected; quoted `"... since 5 ..."` kept.
   - One test: `heldApproval.at` is stamped, a given `at` is rejected. Update existing rows that send `HELD` with `at`.
   - A test that `now` prints the format and `--iso` prints an ISO time.
3. Docs under `agent-team/.claude/skills/chief-of-staff/`: `state-keys.md` (state example, `status` key, `heldApproval` key), `SKILL.md` § State file example, `status.md`, `approvals.md` (awaiting-review line, § Ticket comment on approval), `review.md`, `commands.md`, `send-or-queue.md`: examples use `since {since}`; every `<time>` in a comment says to take it from `python3 ~/.collective-wisdom/scripts/cos_state.py now`; `heldApproval` examples drop `at`.

## Verify

`python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
