# As-built: Make the dashboard top-level section headers collapsible

**Shipped:** in PR #383
**Ticket:** CW-369
**Spec:** [2026-11-14-cw-369-collapsible-top-headers-design.md](../specs/2026-11-14-cw-369-collapsible-top-headers-design.md)

## Differs from the spec

- The spec makes Done collapsible with a `band:done` key and a start-up step. #350 moved Done to its own tab before this merged, so there is no Done header on the Ship loop tab and nothing shipped for it. The other five sections are as specified.
- The spec's tests list a check that every band key starts with `band:` and matches no group name. It was left out as a test of a constant (`AGENTS.md` § Testing); the case where a group name in the saved set collapses no band covers the behavior.
