# As-built: Remove a ticket from the dashboard Todo list when it leaves Todo

**Shipped:** in PR #381
**Ticket:** CW-355
**Spec:** [2026-11-14-cw-355-todo-list-stale-design.md](../specs/2026-11-14-cw-355-todo-list-stale-design.md)

## Differs from the spec

- The spec does not touch the approval path. `cos_state.py` now imports `cos_lists.py`, so `cos_lists.py` is added to `HANDS_SCRIPTS` in `approval_policy.py`, which the approval-path import test requires.
- The spec says each item gets a `readAt` of ms or null. An item from a list with no or a bad `at` has no `readAt` key at all.
- The spec says the Chief of Staff guardrail line and `org-chart.md` name `cos_state.py apply`. The guardrail line in `chief-of-staff/SKILL.md` is unchanged, because it sits in the compaction core and its wording ("only `cos_lists.py` writes `tracker-lists.json`") is still true. The State file paragraph and `org-chart.md` name it.
