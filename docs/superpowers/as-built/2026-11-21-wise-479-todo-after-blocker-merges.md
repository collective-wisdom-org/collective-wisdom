# As-built: Mark tickets Todo when their last blocker merges

**Shipped:** in PR #481
**Ticket:** WISE-479
**Spec:** [2026-11-21-wise-479-todo-after-blocker-merges-design.md](../specs/2026-11-21-wise-479-todo-after-blocker-merges-design.md)

## Differs from the spec

- The spec lists four `stay` reasons. `cos_unblocked.py` also prints `stay <ID> state unknown` and `stay <ID> relations unknown`, so a ticket whose state or relations can't be read never moves (found in code review).
- The spec reads the ticket's state with `pm_hygiene.state_of` on `state`. The script reads `state` (GitHub), `status` (Linear) or `fields.status` (Jira) first.
- readiness.md § Unblocked after a merge step 1 also names the `Blocked by:` search for a GitHub repo whose dependencies probe failed.
- The test table has extra rows: Linear `status`, Jira with no relations, no state at all, and a merged blocker already closed.
