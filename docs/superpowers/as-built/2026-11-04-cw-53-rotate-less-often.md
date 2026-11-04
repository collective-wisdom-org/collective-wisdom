# As-built: Rotate the Chief of Staff thread less often

**Shipped:** in PR #79
**Ticket:** CW-53
**Spec:** [2026-11-04-cw-53-rotate-less-often-design.md](../specs/2026-11-04-cw-53-rotate-less-often-design.md)

## Differs from the spec

- The spec says a `stage` op whose new stage is `spec`, `build` or `merge` stamps `lastRelayAt`. It stamps only when the stage changes, or when a ticket in an active stage gets a new `childThreadId` (a continuation start in the same lane). A repeat `stage` op into the same stage with no new child (a status refresh) does not count as a relay. A `set` op that changes `childThreadId` on an active ticket stamps too.
- The `take-over context=<N>k` check is folded into the expected line of `test_plain_saves_session_and_takeover` instead of added as a column.
