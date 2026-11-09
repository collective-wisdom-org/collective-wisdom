# As-built: Show a short title next to every ticket ID in what the user reads

**Shipped:** in PR #279
**Ticket:** CW-278
**Spec:** [2026-11-09-cw-278-ticket-id-titles-design.md](../specs/2026-11-09-cw-278-ticket-id-titles-design.md)

## Differs from the spec

- The spec drops `[`, `]`, backticks and newlines from a title. The build also drops `<` and `>` (they render as links in the report format), and writes the ID alone when a title contains `Auto-approved`, `BUILD READY`, `MERGE READY`, `BLOCKED:`, `MERGED #` or `CHIEF OF STAFF:`, so a title can't pass for a marker or for the auto-approval notice. `ship-loop/SKILL.md` repeats the rule with a shorter marker list (no `CHIEF OF STAFF:`), and `project-manager/reference.md` only adds `<` and `>` to its drop list.
- The spec's title-source order starts with the line's own source. The build starts with the ticket's `title` in state (or `pm.ranked`), then the one `list-tickets` call, then `get-ticket` for a merged ticket, and uses a child or helper report's own title only after those.
- The `Auto-approved under` notice keeps its current shape, listed beside the other lines that keep theirs.
- Beyond the spec's file list, `rotation.md` (take-over lines) and a few more lines in `continuation.md` and `ticket-helper.md` follow the rule.
