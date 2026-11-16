# CW-343 plan: turn on the context reset for Cursor

**Spec:** [design](../specs/2026-11-15-cw-343-cursor-context-reset-design.md)

## Task 1: `RESET_MODES` and tests

- `agent-team/scripts/cos_rotation_check.py`: `RESET_MODES = {"claudeAgent": "reset", "cursor": "reset"}`; fix the docstring example that says `ok (no reset on cursor; size unknown)`.
- `agent-team/scripts/test_cos_rotation_check.py`: add two `cursor` rows to `test_line_by_reset_mode` (size over the cap, new skill commit); flip the two `cursor` silent cases in the Cursor hook table to a followup (keep a `codex` silent case); drop the `RESET_MODES["cursor"]` patch in the run-store hook test; change the plain-mode `cursor` row to `rotate: size 230k >= 220k; mode reset`.

## Task 2: docs

- `agent-team/.claude/skills/chief-of-staff/rotation.md`: only Codex has mode `none`; the exit-2 fallback names Claude Code and Cursor; take over step 4 says `Take-over context unknown.` when `--record-takeover` prints no `take-over context=`, and skips the 220k Cleanup check.
- `docs/compatibility.md`: Cursor cells of the Context reset and Fresh-context reset rows, the hook bullet, G7, G8, G28 as in the spec. Leave the WISE-441 run entry as written.

## Verify

`python3 -I -m pytest -q agent-team/scripts`
