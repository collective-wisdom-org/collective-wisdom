# As-built: Post the owner's approving review when the user approves a merge

**Shipped:** in PR #89
**Ticket:** CW-87
**Spec:** [2026-11-04-cw-87-owner-approval-from-thread-design.md](../specs/2026-11-04-cw-87-owner-approval-from-thread-design.md)

## Differs from the spec

- The spec's usage line has `[--db PATH] [--file STATE]`. The script takes only the ticket ID, so the caller cannot pick the message store or the state file.
- A state problem the spec doesn't name (no `pr`, a short or missing `headSha`, no `chiefThreadId`, an unusable `lastSeenAt`) is a stop (exit 1) with its reason. A missing `Owner login` in project.md, or a state file or gh reply with an unexpected shape, is exit 2.
- The `merge-pr` BLOCKED line after a push says the child reports MERGE READY again and then the user replies `approve N` (or approves on GitHub), because the ticket is `blocked`, not `awaiting-merge`, at that point.
