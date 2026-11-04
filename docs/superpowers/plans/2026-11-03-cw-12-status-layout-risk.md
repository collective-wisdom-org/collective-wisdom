# Grouped `status` layout and risk levels (CW-12) implementation plan

Spec: `docs/superpowers/specs/2026-11-03-cw-12-status-layout-risk-design.md` (approved at cbe646e). Edit only `agent-team/.claude/skills/chief-of-staff/SKILL.md` (plus the docs under `docs/superpowers/`). Prose only: no script or test changes. Test command: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh agent-team/scripts/*.sh`. Both must stay green.

Keep the diff inside three places so PR #26 (CW-17) rebases cleanly: the `status` row of § Commands, § Approval requests, § Report format. Prose follows `human-writing`: plain sentences, no em dashes.

## Task 1: § Approval requests

- Spec block first line becomes `<PREFIX>-210 spec ready: Example feature. Risk: Low (docs only, 3 Builds bullets)`. Merge block first line: `<PREFIX>-197 merge ready: <PR title>. Risk: High (touches auth)`. `Touches:` and `Risks:` stay as they are.
- Both reminder lines start with `<Level> (<reason>): ` before the ticket ID. Add the note that this is the one report line that does not start with the ticket ID.
- Add `### Risk level` at the end of the section, per spec Design 2: High/Medium/Low table, "small" thresholds (merge: 5 files or fewer; spec: 4 Builds bullets or fewer), higher level wins, reason in a few words, kept at the end of the ticket's `status` line as `Risk: <Level> (<reason>).` and carried into every later `status` line until a new block replaces it, `Risk: not rated yet` before any block, and the "informs only, never approves or skips a gate" rule.

## Task 2: § Report format

- `Needs you` example: update the spec block first line and the merge reminder line to match Task 1.
- Add `### Status layout` at the end of the section, per spec Design 3: one table per group under a bold header with count, example, group-to-stage table, and the rules (empty groups drop out, risk and detail from the `status` line, titles from the existing tracker read, sweep findings, `Merged:` line, `Filling stopped:` line, full blocks for pending approvals, no other report sections, `where's <PREFIX>-N?` variant).

## Task 3: § Commands `status` row

Replace "answer from state plus the tracker, with thread links" with a pointer to § Report format "Status layout". Keep the idle check, sweep and "post the full block again" sentences.

## Verify

`git diff origin/main --stat` shows only the SKILL.md change plus docs. Run the test and lint commands. Check each Acceptance line in the ticket maps to text in the diff.
