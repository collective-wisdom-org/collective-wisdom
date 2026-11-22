# As-built: Keep the dashboard tab counts on one line

**Shipped:** in PR #493
**Ticket:** WISE-492
**Spec:** [2026-11-22-wise-492-tab-counts-one-line-design.md](../specs/2026-11-22-wise-492-tab-counts-one-line-design.md)

## Differs from the spec

- The spec says only overflow and wrapping change. The build also adds `.tabs button:focus-visible { outline-offset:-2px; }`, because `overflow-x:auto` on the bar clipped about 1px of the keyboard focus ring.
- The `scrollIntoView` call is optional (`tab.scrollIntoView?.(...)`) so non-browser test runs don't throw.
