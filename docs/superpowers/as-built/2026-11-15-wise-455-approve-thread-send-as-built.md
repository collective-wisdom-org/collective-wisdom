# As-built: Confirm dashboard Approve and Mark todo sends

**Shipped:** in PR #457
**Ticket:** WISE-455
**Spec:** [2026-11-15-wise-455-approve-thread-send-design.md](../specs/2026-11-15-wise-455-approve-thread-send-design.md)

## Differs from the spec

- The spec reads the press body with a 256-byte cap only. The build also gives up after 2 seconds if the body has not ended, so a stalled request cannot hold the press lock, and it closes the connection once the 400 is written.
- The spec says the 3-second limit comes first, as today. The build sets the limit time only after a valid command, so a rejected body does not start the 3 seconds.
- `checkSentPy` has an optional fourth parameter, `db`, that adds `--db <path>`. Only a test passes it.
- The spec adds no test for the check script's exit-code mapping. The build adds one table test that runs the real `cos_user_check.py` through `checkSentPy` against a fixture message table.
