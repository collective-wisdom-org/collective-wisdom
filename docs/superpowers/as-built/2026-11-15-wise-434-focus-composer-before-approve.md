# As-built: Focus the T3 composer before the dashboard presses Return on Approve

**Shipped:** in PR #450
**Ticket:** WISE-434
**Spec:** [2026-11-15-wise-434-focus-composer-before-approve-design.md](../specs/2026-11-15-wise-434-focus-composer-before-approve-design.md)

## Differs from the spec

- The spec chose setting `AXFocused` on the composer. T3 ignores it, so the script clicks the composer's center instead (mouse warped straight back). The spec text already says this.
- Mark todo shares the press route (merged from main), so the `no-focus` line starts with the control's name (`Approve` or `Mark todo`), not always `Approve`.
- No press-route test row for `no-focus`; the `pressResult` and `pressMessage` tables cover it.
- Before clicking, the script hit-tests the composer's center with `AXUIElementCopyElementAtPosition` and clicks only when the composer (or a child of it) is at that point, so an overlay or another app's window is never clicked. The final "T3 is in front" check reads `AXFrontmost` on the app. Both came from review.
