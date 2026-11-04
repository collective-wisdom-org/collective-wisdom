# As-built: Project manager hygiene child

**Shipped:** in PR #78
**Ticket:** CW-56
**Spec:** [2026-11-04-cw-56-pm-hygiene-child-design.md](../specs/2026-11-04-cw-56-pm-hygiene-child-design.md)

## Differs from the spec

- The spec's child task text says "§ Hygiene pass step 6". With the Todo fill gone the pass has five steps, so the text says step 5.
- § Backlog pick step 3: a ticket that fails the readiness check does not take the slot, and the pick tries the next `ready` entry, like the Todo branch of the slot fill. The spec did not say.
- `lastDailyAt` is added to the `pm` JSON example in `project-manager/SKILL.md` § State.
- The org chart's "Where the user approves" diagram gets a dotted Backlog to Spec edge for the ranked pick.
