# As-built: An awaiting-review stage for PRs waiting on a teammate's review

**Shipped:** in PR #141
**Ticket:** CW-128
**Spec:** [2026-11-05-cw-128-awaiting-review-design.md](../specs/2026-11-05-cw-128-awaiting-review-design.md)

## Differs from the spec

- The spec named two helpers in `merge_pr.py`, `review_names` and `review_stop`. CW-127 and #140 landed the rule as `required_reviews(f)` and `teammate_approval(f)`, so the build adds `review_stop(f)`, `latest_verdicts(f)` and `requested_names(f)` around them. `gate()` behaves as before.
- A codeowner login passes `REVIEW_REQUIRED` at the merge gate (#140), so for that login the review check does too. With `Require teammate approval` `on`, the teammate rule still holds the ticket.
- `changes` fires only when the changes request is on the ticket's current head. The spec fired on any standing request, which would have sent the child back to build in a loop after every fix push. A request on an older head, one already relayed, or a `reviewDecision` of `CHANGES_REQUESTED` with no review on the head, reads as `waiting`, and `needs` names the reviewers who must look again.
- `--route` sends a PR whose `reviewDecision` is `CHANGES_REQUESTED` to `awaiting-review` even with the row off, so it follows the standing request as the merge gate does.
- Only reviews from an owner, member or collaborator of the repo count, as in the merge gate.
- `cos_sweep.py` takes a `--review-prs FILE` flag, so the review part can be tested with fixtures.
- The `ship-loop` relay bullet sits under § Changes requested, because #131 removed the Team mode heading. `state-keys.md` carries the same-head cut-off exception in the `lastSeenAt` entry.
- A ticket key `changesRelayed` records the changes request that was relayed. `changes` fires only for a request on the head newer than it, so a child that answers in a PR comment and pushes nothing can report `MERGE READY` again and wait for the reviewer. The `changes` line ends with `at <time>` of that request.
- `approved ... by <x>` names the approvers on the head whatever the row says. `x` is `github` when only GitHub's decision approved, `codeowner` when the codeowner bypass passed the required review, and `none` when nothing was required and nobody approved.
- Withdrawing a held approval (`hold N`) restamps `lastSeenAt`, so the withdrawn `approve N` no longer verifies. `heldApproval` must carry a full `head`, `itemId` and `at`.
- A ticket with no `pr` or full `headSha` prints `unreadable`, and a merged PR prints no line (the merged check owns it).
- For an `approved` line whose `by` is `codeowner` or `none`, the Chief of Staff does not say a teammate approved: the reminder reads `ready to merge, waiting on you`, and a held approval's report line leaves the approvers out.
- An `unreadable` line for a ticket with no `pr` or a short `headSha` moves the ticket to `blocked`, since that state defect never clears on a retry. A failed GitHub read still retries on the next sweep.
