# As-built: Approve presses Return in T3 Code

**Shipped:** in PR #425
**Ticket:** WISE-423
**Spec:** [2026-11-15-wise-423-approve-keypress-design.md](../specs/2026-11-15-wise-423-approve-keypress-design.md)

## Differs from the spec

- A `busy` answer is silent only for a repeat click on the same ticket. A click on a different ticket during the wait shows `Approve not sent: another Approve was still being sent. Press Send in the Chief of Staff thread.` The spec says `busy` shows nothing.
- A modified or non-primary click (meta, ctrl, shift, alt, or a button other than the left one) presses nothing. The spec presses on every click.
- The `permission` line also tells the user to allow Automation (control System Events), because error -1743 is an Automation problem. The spec names only Accessibility.
- `GET /` also sends `frame-ancestors 'none'` in the CSP and `X-Frame-Options: DENY`, so no other page can frame the dashboard and click through its Approve. Found in review; the spec does not list them.
- The spec's Calls gains the accepted trade-off that, once Accessibility is granted, any process under T3 Code can press keys too.
