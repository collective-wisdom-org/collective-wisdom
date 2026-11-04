# As-built: Retire PR 32 and add its missing --wait test rows

**Shipped:** in PR #50
**Ticket:** CW-40 (#40)
**Spec:** [2026-11-03-cw-40-retire-pr-32-wait-tests-design.md](../specs/2026-11-03-cw-40-retire-pr-32-wait-tests-design.md)
**Plan:** [2026-11-03-cw-40-retire-pr-32-wait-tests.md](../plans/2026-11-03-cw-40-retire-pr-32-wait-tests.md)

## What shipped

- `agent-team/scripts/test_cos_idle_check.py`: three new rows in `test_wait_tells_waiting_child_from_stalled`.
  - A wait call cut off before `"structuredContent"` with `content` whole gives `waiting ABC-1`. It is the only test of the escaped-quote branch of `MATCHED_RE`.
  - A wait call cut off before `"output"` gives exit 2.
  - A whole wait call with `content` and no `structuredContent` gives `waiting ABC-1 on bg1`. It fails if the `content` fallback in `matched_ids` is removed.
- New test helpers `wait_call` and `cut_before`; `wait_read` takes `content` and `structured` options. Existing rows keep their output.
- Comment on PR #32: superseded by CW-21 (#34), with the short comparison. #32 stays open for the user to close.
- No change to `cos_idle_check.py`, skills or docs.

## Differs from the spec

Nothing.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` (run as `uvx pytest -q agent-team/scripts`): 422 passed.
- `shellcheck install.sh agent-team/scripts/*.sh`: clean.
- By hand on scratch copies: the content-only row fails with the `content` fallback removed; the cut-off row fails with `MATCHED_RE` reduced to plain quotes.
