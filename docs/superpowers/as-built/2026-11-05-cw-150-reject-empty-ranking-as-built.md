# As-built: Reject an empty Backlog ranking when the Backlog has open tickets

**Shipped:** in PR #158
**Ticket:** CW-150
**Spec:** [2026-11-05-cw-150-reject-empty-ranking-design.md](../specs/2026-11-05-cw-150-reject-empty-ranking-design.md)

## Differs from the spec

- Count step: the approved spec had one `list-tickets` call and dropped `agent-skip` tickets and parents of tickets in the list. An epic whose sub-tickets are all outside the Backlog is not the parent of another ticket in the list on any tracker, so epics would have been counted. The shipped step also calls `list-children` (limit 1) on the tickets left, one at a time, on every tracker, skips each epic and stops at the first ticket with no sub-ticket, then passes `--backlog-count 1` (or 0 when every ticket left is an epic). This goes past the ticket's "one extra tracker call" budget (usually one extra call, up to the number of tickets left when they are all epics), because the Acceptance item needs epics dropped.
- Author filter: the approved spec did not mention it. The shipped step applies the tracker adapter's author filter to the `list-tickets` call, so tickets from untrusted authors are not counted.
- Reject message: the spec said `cos_rank: empty ranking but the Backlog has N rankable tickets`. It shipped as `cos_rank: empty ranking but the Backlog has at least N rankable ticket(s)`, with "ticket" when N is 1. "At least" is true because the count can stop early at 1.
- Bound on the count: the spec accepted any whole number of 0 or more. The script now accepts 1 to 4 digits, so a very long digit string never reaches `int()`. A longer count is a usage error (exit 2).
- Blocker limit: the spec did not say how tickets with an open blocker count. They still count as rankable, so a Backlog where every ticket is blocked is rejected until a blocker clears. This is now written down in `reference.md` and in the spec's "Leaves out".
