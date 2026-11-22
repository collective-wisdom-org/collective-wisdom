# Send or queue

Read this for any relay to a child, `cos_route.py`, and a plan line `send`, `configure`, `head-check`, `user-check`, `continuation`, `merge-wait` or `run-wait`.

## Send or queue

Every relay that puts a child back to work goes through here. Run `python3 ~/.collective-wisdom/scripts/cos_route.py <PREFIX>-N <caller> --thread <this thread's id> --relay --next`, with the user's words on stdin (an auto-approval: `--auto <tolerance> [--risk "<Level> (<reason>)"]`, no stdin), and do what each `next:` line says. The `relay:` text is what you send, or store in `pendingRelay`.

Callers:

- `approve-spec`, `approve-merge` (`approve N`, or an auto-approval), `changes`, `answer` (a blocked ticket's answer, or an answer to a pending request), `resume` (tickets stopped by the user), `rate-limit` (cleared).
- `reviewer-changes` (relay: review.md § Review check) and `head-moved` (review.md's `moved` line, or the head check below).
- `conflict-keep`, `conflict-stand`, `conflict-withdraw`: the head check, `conflict: yes` in an approval request, or a `BLOCKED:` merge child.

`cos_head_check.py` prints the `head-moved` and `conflict-*` relays. Not callers: the stuck-check restart and approvals.md § Approval requests send-backs.

The user's spec approval relay has a second line, `Approval in thread: <thread id>` (the thread where they wrote it: your own for an immediate one, the stored line for a queued one); a queued one stores both lines in `pendingRelay` and the message's item id in `approvalItemId`. An auto-approved spec relay has no thread line and no `approvalItemId`. A merge approval relay has no thread line and no `approvalItemId` (`cos_approve_pr.py` checks the user's message first); a queued one keeps its place.

Before sending a queued spec approval, run `python3 ~/.collective-wisdom/scripts/cos_user_check.py item <thread in its Approval in thread: line> <approvalItemId>` with the quoted words on stdin (quoted heredoc).

- Exit 1 (`reject: …`): don't send. Drop the queued relay, `cos_state.py comment withdrawn` with `the approval message could not be verified` on stdin, report it under Needs you.
- Exit 2: `t3_thread_read` that thread with `itemId: <approvalItemId>` and `maxCharsPerItem: 500`; `createdBy` must be `"user"` and the text must contain the quoted words. Add one Cleanup line, `User check script unavailable; used thread read`.

An approval sent at once uses the item id from verifying the command (commands.md § Commands).

A queued auto-approved relay skips that check. Run `python3 ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec` (a spec) or `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto` (a merge) again just before the send. Anything but exit 0: don't send. Drop the relay, `comment withdrawn` with `the auto-approval no longer holds`, set the stage back to `awaiting-build` or `awaiting-merge`, ask the user as usual. When a queued auto spec relay passes and goes out, first post `<PREFIX>-N: Auto-approved under <tolerance>; the build has started.` in the sending thread: the child reads that thread for the notice (ship-loop § Approvals).

**Continuation child.** A relay (at once or from the queue) to a ticket whose `parentThreadId` is known and is not `chiefThreadId`: read continuation.md § Continuation child.

**Verify a merge approval**, after the head check and before the relay is sent or queued: `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N`. Exit 0 (`verified`): build the merge relay (only after this exit 0 in this run) and send or queue it. Exit 1 or 2: don't send or queue, keep `awaiting-merge`, tell the user under Needs you with the script's last line; `approve N` can be sent again once fixed. Exit 2 never falls back to a thread read.

**Verify an auto-approved merge**, same timing: `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto`. Exit 0 (`auto-approved`): post the merge block as a notice (approvals.md § Auto-approval), send or queue the relay. Exit 1 or 2: as above, but ask with the normal approval request plus the script's last line under Needs you.

**Head check for a merge approval**, before the relay is sent or queued and again before a queued one is sent: `python3 ~/.collective-wisdom/scripts/cos_head_check.py <PREFIX>-N --next`. It prints the relay to send (the conflict relay names the verified head, never sent for another), then its last line and a `next:` line: do what it says.

The ticket comment on an approval: approvals.md § Ticket comment on approval.
