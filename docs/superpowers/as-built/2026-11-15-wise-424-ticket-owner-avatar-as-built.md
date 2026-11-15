# As-built: WISE-424 ticket owner avatar

**Shipped:** in PR #427
**Ticket:** WISE-424
**Spec:** [2026-11-15-wise-424-ticket-owner-avatar-design.md](../specs/2026-11-15-wise-424-ticket-owner-avatar-design.md)

## Differs from the spec

- The spec puts the badge in the head beside the copy button. It shipped on the first row of the card (the ticket id row), right-aligned at the card's top right; the title and copy button stay on the second row.
- The viewer is read by a new `viewer.ts` (`createViewer`), and `startServer` takes an optional `viewerGh` runner for it so tests can inject a login.
- The avatar `<img>` carries `referrerpolicy="no-referrer"`, which the spec's markup does not.
- The login rule is one exported `loginOf` in `titles.ts`, shared by `merged.ts`, `open.ts`, `backlog.ts` and `viewer.ts`, not repeated in each file.
