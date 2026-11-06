# As-built: Leave only project.md from the team in a consuming repo

**Shipped:** in PR #166
**Ticket:** CW-161
**Spec:** [2026-11-06-cw-161-project-md-only-design.md](../specs/2026-11-06-cw-161-project-md-only-design.md)

## Differs from the spec

- The spec's removal command deletes every listed file the app has. As built, a listed file reached through a link that leaves the app (a symlinked parent folder) is skipped with a `skip  <path>` line and not touched, so the command never writes outside the app.
