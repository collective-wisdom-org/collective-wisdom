# As-built: Leave only project.md from the team in a consuming repo

**Shipped:** in PR #166
**Ticket:** CW-161
**Spec:** [2026-11-06-cw-161-project-md-only-design.md](../specs/2026-11-06-cw-161-project-md-only-design.md)

## Differs from the spec

- The spec's removal command deletes every listed file the app has. As built, a listed file reached through a link that leaves the app (a symlinked parent folder) is skipped with a `skip  <path>` line and not touched, so the command never writes outside the app.
- The pin, each of the five roots and `.agents/skills` are skipped too when they are reached through a link that leaves the app.
- The pin is deleted after the other files and folders, and its own folder right after it. The spec says files, then pin, then folders.
- A delete that fails stops the run with exit 1, and the message says whether the pin is still there or already gone, so a rerun is safe.
