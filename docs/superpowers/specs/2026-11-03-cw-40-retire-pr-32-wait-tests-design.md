# Retire PR 32 and add its missing --wait test rows (design)

**Status:** Shipped
**Ticket:** CW-40 (#40)

## Intent

PR #32 ports a change that CW-21 (PR #34) already put on `main`. The only thing #32 has that `main` lacks is test coverage in `test_wait_tells_waiting_child_from_stalled`. Port that coverage, and leave a comment on #32 so the user can close it.

## What the two #32 rows really test

I checked the ticket's reading of the two rows against `main`'s `cos_idle_check.py` (`e835684`) by removing code and rerunning them:

| Case | Result on `main` | Fails when the `content` fallback in `matched_ids` is removed | Fails when `MATCHED_RE` stops accepting escaped quotes (`\\*`) |
|---|---|---|---|
| Wait call cut off just before `"structuredContent"`, `content` whole | `waiting` (exit 0) | no | yes |
| Wait call cut off just before `"output"` | exit 2 | no | no |
| Whole wait call whose output has only `content` (new) | `waiting ... on bg1` (exit 0) | yes | no |

Cut-off text fails `json.loads`, so `wait_calls` decides it with the regexes and never calls `matched_ids`. The first #32 row is still worth having: `main` has no test that the escaped `\"matched\": [\"` inside `content` counts as a match. It just doesn't test the fallback. The ticket's acceptance line "fail if the `content` fallback in `matched_ids` is removed" needs a third row: a whole call with `content` and no `structuredContent`.

## Design

- `agent-team/scripts/test_cos_idle_check.py`:
  - `wait_read` gets a way to write `output.content` (the same `{"matched", "unmatched"}` object, JSON-encoded, as the real tool sends) next to `structuredContent`, and a way to leave `structuredContent` out. Existing rows keep their current output.
  - A small helper cuts a call's JSON text just before a given key, as `maxCharsPerItem` does.
  - Three new rows in `test_wait_tells_waiting_child_from_stalled`:
    1. cut off before `"structuredContent"` with `content` whole: exit 0, `waiting ABC-1`
    2. cut off before `"output"`: exit 2, `cos_idle_check:`
    3. whole call, `content` only: exit 0, `waiting ABC-1 on bg1`
- No change to `cos_idle_check.py`, skills or docs.
- Comment on PR #32 (through `./scripts/gh.sh pr comment 32`): superseded by CW-21 (#34), the short comparison from the ticket, and that its one gap (the test rows) went into this ticket's PR. #32 stays open; the user closes it. Posted in the build stage, after the CW-40 PR exists so the comment can link it.

## Calls I made

- Added a third row (whole call, `content` only) beyond the two the ticket names, because neither of those two fails when the fallback is removed. Without it the ticket's own acceptance line can't be met.
- Kept the "cut off before `structuredContent`" row even though it tests the escaped-quote regex, not the fallback. It is the only test of that regex branch.
- Kept the "cut off before `output`" row though it overlaps `main`'s existing cut-off row (exit 2): it cuts at a different point (no output at all), it is one line, and the ticket asks for it.
- Post the #32 comment after opening the CW-40 PR, so it can link it.
- Closeout docs (as-built, index, release note) ship in the PR as usual. The release note says nothing changes for users.

## Out of scope

- #32's wording changes, its Tools-line mention of `--wait`, and its closeout docs.
- Closing or merging #32.

## Verification

- The three rows pass on `main`'s script. Row 3 fails with the fallback in `matched_ids` disabled; row 1 fails with `MATCHED_RE` reduced to plain quotes. Checked by hand on a scratch copy, not committed.
- `python3 -I -m pytest -q agent-team/scripts` passes and `shellcheck install.sh agent-team/scripts/*.sh` is clean.
- #32 has the comment and is still open.
