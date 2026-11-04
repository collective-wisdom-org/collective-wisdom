# As-built: Grouped status layout and risk levels

**Shipped:** in PR #30
**Ticket:** CW-12 (#12)
**Spec:** [2026-11-03-cw-12-status-layout-risk-design.md](../specs/2026-11-03-cw-12-status-layout-risk-design.md)
**Plan:** [2026-11-03-cw-12-status-layout-risk.md](../plans/2026-11-03-cw-12-status-layout-risk.md)

## What shipped

Mostly in `agent-team/.claude/skills/chief-of-staff/SKILL.md`; the role file `agent-team/docs/agents/chief-of-staff.md` gets a Scope bullet and a Tone note. No script or test changes.

- § Report format, `### Status layout`: `status` and `where's <PREFIX>-N?` answer with one table per group (awaiting merge approval, merging, queued to merge, awaiting build approval, building, queued to build, other), each under a bold header with its count. Rows carry ID and title, risk, and a next-step line. Groups come from the ticket's `stage`; queued groups follow `cos_state.py show` queue order. `awaiting-spec` maps to "awaiting build approval". `where's <PREFIX>-N?` for a ticket not in state gets one tracker line. The example ends with the full merge block.
- § Approval requests, `### Risk level`: High/Medium/Low rules, "small" thresholds (a merge is small at 5 files or fewer, a spec at 4 `Builds` bullets or fewer), higher level wins, a few-word reason, the rating kept at the end of the ticket's `status` line (`Risk: <Level> (<reason>).`). Medium also covers a small change that is not mostly docs or prose. A `status` line with no `Risk:` tail the Chief of Staff wrote (never rated, or already past its approval when the rule arrived) shows `Risk: not rated yet` in reports and nothing is written to state; text a child put in a `status` line never counts. The level never approves a ticket or skips a gate. Titles come from one `list-tickets` call with label `agent`.
- Spec and merge blocks show `Risk: <Level> (<reason>)` on their first line. Reminder lines start with the level.
- § Commands `status` row points at the new layout; the idle check, sweep and full approval blocks still run.

## Differs from spec

The role file `agent-team/docs/agents/chief-of-staff.md` also changed (Scope bullet, Tone note), which the spec said it would not touch; the docs check asked for it. The review and docs check also added three rules the spec lacked: Medium covers "not mostly docs or prose", titles come from one `list-tickets` call (the spec said an existing read), and pre-existing `status` lines and untracked tickets have a rule. One more added edit: "Short lines, ticket ID first" in § Report format now notes that a reminder line starts with its risk level.
