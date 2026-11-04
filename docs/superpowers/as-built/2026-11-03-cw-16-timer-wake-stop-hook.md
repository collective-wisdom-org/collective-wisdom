# As-built: Timer, scheduled wake and Stop-hook decision

**Shipped:** in PR #36
**Ticket:** CW-16 (#16)
**Spec:** [2026-11-03-cw-16-timer-wake-stop-hook-design.md](../specs/2026-11-03-cw-16-timer-wake-stop-hook-design.md)

## What shipped

- One sentence in `chief-of-staff` SKILL.md § Send or queue, first bullet: a relay sent to a child whose `parentThreadId` isn't the Chief of Staff thread adds a Moving line, `<PREFIX>-N: I may not hear when this run ends; say status to check.`
- The spec, plan, as-built, index entry and release note for the decision ticket.
- One comment on #16 recording the five answers: no timer, no scheduled wake, no new Stop-hook check, the wait isn't a real cost yet, and yes to the report line.

## Differs from the spec

Nothing.

## Verification

`python3 -I -m pytest -q agent-team/scripts` passes (327 tests) and `shellcheck install.sh agent-team/scripts/*.sh` is clean. The diff touches only that bullet in the skill, plus `docs/superpowers/`.
