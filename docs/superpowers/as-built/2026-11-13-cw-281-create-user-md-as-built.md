# As-built: Have the Chief of Staff create user.md when this machine has none

**Shipped:** in PR #292
**Ticket:** CW-281
**Spec:** [2026-11-13-cw-281-create-user-md-design.md](../specs/2026-11-13-cw-281-create-user-md-design.md)

## Differs from the spec

- The spec says the check skips only the second pass through the start-up clean-up in `resume`. It also skips the `wake` command, because `wake` runs only clean-up step 1 (the SKILL.md `wake` row refers to that step by number, so the steps were not renumbered). startup.md § User settings check says so.
