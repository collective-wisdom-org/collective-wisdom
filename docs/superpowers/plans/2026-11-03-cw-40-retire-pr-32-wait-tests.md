# Retire PR 32 and add its missing --wait test rows (plan)

**Ticket:** CW-40 (#40)
**Spec:** [2026-11-03-cw-40-retire-pr-32-wait-tests-design.md](../specs/2026-11-03-cw-40-retire-pr-32-wait-tests-design.md)

## Task 0: test rows

All edits are in `agent-team/scripts/test_cos_idle_check.py`. No change to `cos_idle_check.py`.

1. `wait_read` gets two options: `content=True` also writes `output.content` (the `{"matched", "unmatched"}` object as a JSON string, as the real tool sends it), and `structured=False` leaves `structuredContent` out. Existing rows keep their output.
2. Add a small helper `cut_before(call_text, key)` that returns the call's JSON text up to just before `"key"`, as `maxCharsPerItem` cuts it.
3. Add three rows to `test_wait_tells_waiting_child_from_stalled`:
   - cut off before `"structuredContent"`, `content` whole: exit 0, `waiting ABC-1`
   - cut off before `"output"`: exit 2, `cos_idle_check:`
   - whole call, `content` only (no `structuredContent`): exit 0, `waiting ABC-1 on bg1`
4. Check on a scratch copy, not committed: row 3 fails with the `content` fallback in `matched_ids` removed; the first row fails with `MATCHED_RE` reduced to plain quotes.

Test lines added stay small (budget: no more than the feature code, which is none, so keep it to the three rows and the two helpers).

**Verify:** `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh`.

## Task 1: PR 32 comment

After the CW-40 PR exists, post a comment on #32 with `./scripts/gh.sh pr comment 32 --body-file <path>`: superseded by CW-21 (#34), a short comparison, and that its test rows went into the CW-40 PR. #32 stays open.

## Task 2: closeout docs

As-built, index entry and release note per `open-pr` § Closeout docs. The release note says nothing changes for users.
