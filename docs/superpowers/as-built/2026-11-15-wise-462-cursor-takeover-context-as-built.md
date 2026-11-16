# As-built: Read the take-over context size on Cursor

**Shipped:** in PR #473
**Ticket:** WISE-462
**Spec:** [2026-11-15-wise-462-cursor-takeover-context-design.md](../specs/2026-11-15-wise-462-cursor-takeover-context-design.md)

## Differs from the spec

- The spec says the `--hook` path "never fills" a pending take-over size. The hook does use the filled size to decide, and never saves it. Without that, a take-over that lands above 220k would send `rotate: size` from the Stop hook and reset again, since Cursor's reset mode is `reset` (#468), not `none` as the spec's "Today" assumes.
