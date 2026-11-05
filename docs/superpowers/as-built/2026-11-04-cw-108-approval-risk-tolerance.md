# As-built: Approval risk tolerance

**Shipped:** in PR #119
**Ticket:** CW-108
**Spec:** [2026-11-04-cw-108-approval-risk-tolerance-design.md](../specs/2026-11-04-cw-108-approval-risk-tolerance-design.md)

## Differs from the spec

- The spec does not cover queued relays. Queue and continuation code recognised approvals only by the prefix `CHIEF OF STAFF: the user approved`, so `continuation.md`, `state-keys.md` and the queue wording in chief-of-staff `SKILL.md` now handle `auto-approved` relays too. A queued auto relay stores no `approvalItemId`, and the auto check runs again just before it is sent.
- `agent_usage.py` files the cost of `CHIEF OF STAFF: auto-approved the merge` under the merge stage.
- `cos_approve_pr.py --auto` stops when the PR has 100 or more files, because `gh` returns at most 100 and the approval-path and flag checks could not cover the rest.
- `approval_policy.py` accepts `-h` and `--help` (exit 0).
- `project_config.py` also has `approval_setting()`, which returns the level and the reason for a fallback to `strict`.
- The `Risk:` tail is read from the first `Risk: ` in the status line and needs a valid level followed by a parenthesised reason.
- `approval_policy.py check` ends with `approval: auto spec under <tolerance> (Risk: <Level>)` or `approval: ask (<why>)`; the spec gave no format.
