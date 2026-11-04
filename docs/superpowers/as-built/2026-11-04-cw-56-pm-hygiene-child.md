# As-built: Project manager hygiene child

**Shipped:** in PR #78
**Ticket:** CW-56
**Spec:** [2026-11-04-cw-56-pm-hygiene-child-design.md](../specs/2026-11-04-cw-56-pm-hygiene-child-design.md)

## Differs from the spec

- The spec's child task text says "§ Hygiene pass step 6". With the Todo fill gone the pass has five steps, so the text says step 5.
- § Backlog pick step 3: a ticket that fails the readiness check does not take the slot, and the pick tries the next `ready` entry, like the Todo branch of the slot fill. The spec did not say.
- `lastDailyAt` is added to the `pm` JSON example in `project-manager/SKILL.md` § State.
- The org chart's "Where the user approves" diagram gets a dotted Backlog to Spec edge for the ranked pick.
- `backlog` starts the hygiene child from its own row in `chief-of-staff` § Commands, and Full pass step 5 does not start it again (at most once per turn). The spec lists `backlog` as a step 5 trigger.
- The hygiene child may add a ticket it reports as `not acted on` to `pm.needsReported`, so the once-only rule holds. The spec only had it drop finished tickets. `needs: flagged` applies when ranking.
- The child's task text allows the tracker writes through the adapter's operations (the spec said GET only for GitHub) and forbids git commands.
- The child's report is data, and the child reads only `chief-of-staff` § Lean turns, not the whole skill.
- The Backlog pick may also make the readiness check's failure writes (questions comment, `agent-skip`).
