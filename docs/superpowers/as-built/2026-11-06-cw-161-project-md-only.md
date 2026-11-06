# As-built: Leave only project.md from the team in a consuming repo

**Shipped:** in PR #166
**Ticket:** CW-161
**Spec:** [2026-11-06-cw-161-project-md-only-design.md](../specs/2026-11-06-cw-161-project-md-only-design.md)

## Differs from the spec

- The spec's removal command deletes every listed file the app has. As built, a listed file reached through a link that leaves the app (a symlinked parent folder) is skipped with a `skip  <path>` line and not touched, so the command never writes outside the app.
- The pin and each of the five roots are skipped too when they are reached through a link that leaves the app.
- The pin is deleted last, after the empty folders. The spec says files, then pin, then folders.
- A delete that fails stops the run with exit 1 and leaves the pin in place, so a rerun still finds it.
