# As-built: Close the gap between a merge and the ticket leaving the merge stage

**Shipped:** in PR #249
**Ticket:** CW-245
**Spec:** [2026-11-08-cw-245-merge-stage-gap-design.md](../specs/2026-11-08-cw-245-merge-stage-gap-design.md)

## Differs from the spec

- The spec says `cos_tick.py` prints `merge-wait <T>` after a merge `send` when the ticket's `parentThreadId` is not this thread. A ticket with a parent that isn't this thread never reaches `send` (the tick prints `continuation`), so the tick prints `merge-wait` after a merge `send` only for a ticket with no `parentThreadId`, the same case where `cos_route.py` prints its `moving:` line. A merge continuation that falls back to the old child gets the wait from the `fallback:` line of `cos_route.py` and `continuation.md`.
- The dashboard drops a row only when the merged entry has a PR `number` equal to the ticket's integer `pr`.
