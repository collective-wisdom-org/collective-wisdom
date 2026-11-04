# As-built: Grouped status layout and risk levels

**Shipped:** in PR #30
**Ticket:** CW-12 (#12)
**Spec:** [2026-11-03-cw-12-status-layout-risk-design.md](../specs/2026-11-03-cw-12-status-layout-risk-design.md)
**Plan:** [2026-11-03-cw-12-status-layout-risk.md](../plans/2026-11-03-cw-12-status-layout-risk.md)

## What shipped

Mostly in `agent-team/.claude/skills/chief-of-staff/SKILL.md`; the role file `agent-team/docs/agents/chief-of-staff.md` gets a Scope bullet and a Tone note. No script or test changes.

- § Report format, `### Status layout`: `status` and `where's <PREFIX>-N?` answer with one table per group (awaiting merge approval, merging, queued to merge, awaiting build approval, building, queued to build, other), each under a bold header with its count. Rows carry ID and title, risk, and a next-step line. Groups come from the ticket's `stage`; queued groups follow `cos_state.py show` queue order. `awaiting-spec` maps to "awaiting build approval".
- § Approval requests, `### Risk level`: High/Medium/Low rules, "small" thresholds (a merge is small at 5 files or fewer, a spec at 4 `Builds` bullets or fewer), higher level wins, a few-word reason, the rating kept at the end of the ticket's `status` line (`Risk: <Level> (<reason>).`, `Risk: not rated yet` before any block), and the rule that the level never approves or skips a gate.
- Spec and merge blocks show `Risk: <Level> (<reason>)` on their first line. Reminder lines start with the level.
- § Commands `status` row points at the new layout; the idle check, sweep and full approval blocks still run.

## Differs from spec

Nothing. One added edit: "Short lines, ticket ID first" in § Report format now notes that a reminder line starts with its risk level.
