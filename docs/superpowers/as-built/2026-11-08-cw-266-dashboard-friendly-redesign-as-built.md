# As-built: dashboard redesign

**Shipped:** in PR #267
**Ticket:** CW-266
**Spec:** [2026-11-08-dashboard-friendly-redesign-design.md](../specs/2026-11-08-dashboard-friendly-redesign-design.md)

## Differs from the spec

- The spec says each band heading (Your turn, In progress, Up next) shows a muted count after it. It ships without one, because the header sentence already gives the counts and the tests that read the headings would have changed for no gain.
- The spec's example footer reads `3 agents · 41m · $2.10`. It ships with the existing duration format, so the same footer reads `3 agents · 41m 05s · $2.10`.
