# As-built: Show agent spend on the merged PRs in the dashboard

**Shipped:** in PR #211
**Ticket:** CW-209
**Spec:** [2026-11-08-cw-209-merged-pr-spend-design.md](../specs/2026-11-08-cw-209-merged-pr-spend-design.md)

## Differs from the spec

- The spec says a failed write is tried again on the next round. As shipped, the server keeps the last text it actually wrote and retries until a write succeeds, and an empty ledger writes nothing.
- On a merged row, the cost and tokens come after the "merged" time on the second line. The spec did not fix the position.
