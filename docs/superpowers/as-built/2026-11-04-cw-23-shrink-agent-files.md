# As-built: Shrink the files agents load without changing behaviour

**Shipped:** in PR #73
**Ticket:** CW-23 (#23)
**Spec:** [2026-11-03-cw-23-shrink-agent-files-design.md](../specs/2026-11-03-cw-23-shrink-agent-files-design.md)

## Differs from the spec

- The Chief of Staff `SKILL.md` is 60,404 characters, not under 30,000. The spec said to merge #51 and #60 first and to stop with `BLOCKED:` if the target was missed without cutting a rule. #60 had not merged, so Full pass, Slot fill and Lean turns stayed in the core. The build stopped with `BLOCKED:`, and the user chose to ship this as a first PR; #51 and #60 trim further later.
- The total across all touched files is down 0.7%, not 15%, because moved text still counts.
- The build started before #51 was merged. CW-51 and CW-55 merged to `main` during the build, and their edits to the old `SKILL.md` and `reference.md` were ported by hand into the split files. The inventory was re-baselined on `main` at 96b31eb: rows for rules CW-51 removed (G4, O5, O6, O21, O22, O23, O97) are left as gaps and rows for rules it added are appended.
- `test_section_pointers.py` found 9 `§` pointers already broken on `main`. All 9 are fixed in this PR.
- `install.sh --update` adds and updates files but never deletes them, so the install PR in each app must `git rm .claude/skills/chief-of-staff/reference.md`, the file this PR removes. `--check` does not flag the leftover.
- Sizes below are characters.

## Sizes

| File | Before | After |
|---|---|---|
| `agent-team/.claude/skills/build-from-plan/SKILL.md` | 2502 | 2411 |
| `agent-team/.claude/skills/chief-of-staff/SKILL.md` | 101368 | 60404 |
| `agent-team/.claude/skills/chief-of-staff/reference.md (removed)` | 8820 | 0 |
| `agent-team/.claude/skills/chief-of-staff/approvals.md (new)` | 0 | 6215 |
| `agent-team/.claude/skills/chief-of-staff/continuation.md (new)` | 0 | 5486 |
| `agent-team/.claude/skills/chief-of-staff/cross-repo.md (new)` | 0 | 6692 |
| `agent-team/.claude/skills/chief-of-staff/kill-switch.md (new)` | 0 | 1035 |
| `agent-team/.claude/skills/chief-of-staff/rotation.md (new)` | 0 | 13731 |
| `agent-team/.claude/skills/chief-of-staff/startup.md (new)` | 0 | 5276 |
| `agent-team/.claude/skills/chief-of-staff/state-keys.md (new)` | 0 | 4882 |
| `agent-team/.claude/skills/chief-of-staff/status.md (new)` | 0 | 4114 |
| `agent-team/.claude/skills/chief-of-staff/ticket-helper.md (new)` | 0 | 6268 |
| `agent-team/.claude/skills/kickoff-feature/SKILL.md` | 3296 | 2903 |
| `agent-team/.claude/skills/merge-pr/SKILL.md` | 9313 | 7724 |
| `agent-team/.claude/skills/open-pr/SKILL.md` | 11838 | 11367 |
| `agent-team/.claude/skills/project-manager/SKILL.md` | 20600 | 16989 |
| `agent-team/.claude/skills/project-manager/reference.md (new)` | 0 | 3861 |
| `agent-team/.claude/skills/security-review/SKILL.md` | 5619 | 5461 |
| `agent-team/.claude/skills/ship-loop/SKILL.md` | 18045 | 16245 |
| `agent-team/.claude/skills/ship-loop/reference.md (new)` | 0 | 1503 |
| `agent-team/.claude/skills/write-ticket/SKILL.md` | 5391 | 5324 |
| `agent-team/docs/agents/chief-of-staff.md` | 5810 | 5839 |
| `agent-team/docs/agents/code-review.md` | 1072 | 1061 |
| `agent-team/docs/agents/documenter.md` | 3461 | 3486 |
| `agent-team/docs/agents/github-auth.md` | 6229 | 6178 |
| `agent-team/docs/agents/org-chart.md` | 11043 | 9649 |
| `agent-team/docs/agents/personas.md` | 2413 | 2402 |
| `agent-team/docs/agents/security-review.md` | 3571 | 3439 |
| `agent-team/docs/agents/ticket-writer.md` | 569 | 586 |
| `agent-team/docs/agents/trackers/README.md` | 4918 | 4913 |
| `agent-team/docs/agents/trackers/github.md` | 12986 | 12282 |
| `agent-team/docs/agents/trackers/jira.md` | 8230 | 7994 |
| `agent-team/templates/project.md` | 6178 | 5800 |
| **Total** | **253,272** | **251,520** (-0.7%) |
