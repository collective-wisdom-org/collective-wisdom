# As-built: List the running children in reports

**Shipped:** in PR #74
**Ticket:** CW-68
**Spec:** [2026-11-04-cw-68-list-running-children-design.md](../specs/2026-11-04-cw-68-list-running-children-design.md)

## Differs from the spec

- The spec expected CW-23 to merge second and said the `status` layout text would not change. CW-23 merged first (#73), so the edits were re-applied to the split files. `status.md` changed by one word: its "No other `SKILL.md` § Report format section" bullet now lists `Running`, so a `status` answer still never carries it.
- `agent-team/docs/agents/org-chart.md` also changed: the reports edge label now lists `Running`. The spec did not list that file.
