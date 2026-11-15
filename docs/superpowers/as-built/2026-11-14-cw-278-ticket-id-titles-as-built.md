# As-built: Show a short title next to every ticket ID in what the user reads

**Shipped:** in PR #384
**Ticket:** CW-278
**Spec:** [2026-11-14-cw-278-ticket-id-titles-design.md](../specs/2026-11-14-cw-278-ticket-id-titles-design.md)

## Differs from the spec

- The spec's marker-word list (a title holding one is shown as the ID alone) has no `SPEC READY`. The build adds it, because the Chief of Staff still accepts that marker.
- The spec checks for the marker words as plain text. The build ignores case, spaces and the kind of hyphen, so `auto-approved` or `Merge Ready` can't get through.
- The spec's `reference.md` step 3 only widens the line filter. The build also has the Chief of Staff clean the title on each hygiene line it keeps (ID alone on a marker word), and gives the hygiene child the same marker-word rule in its prompt.
