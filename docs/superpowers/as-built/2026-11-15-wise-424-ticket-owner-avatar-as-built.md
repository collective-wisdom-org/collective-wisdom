# As-built: WISE-424 ticket owner avatar

**Shipped:** in PR #PRN
**Ticket:** WISE-424
**Spec:** [2026-11-15-wise-424-ticket-owner-avatar-design.md](../specs/2026-11-15-wise-424-ticket-owner-avatar-design.md)

## Differs from the spec

- The spec puts the badge in the head beside the copy button. It shipped on the first row of the card (the ticket id row), right-aligned at the card's top right; the title and copy button stay on the second row.
- The viewer is read by a new `viewer.ts` (`createViewer`), and `startServer` takes an optional `gh` runner for it so tests can inject a login.
- `createOpenPrs.get()` still returns the number map; its new `owners()` returns the owner map.
