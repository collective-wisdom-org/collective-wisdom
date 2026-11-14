# Send or queue

Read this for any relay to a child, for `cos_route.py`, and for a plan line `send`, `configure`, `head-check`, `user-check`, `continuation` or `merge-wait`.

## Send or queue

Every relay that puts a child back to work goes through here. Run `python3 ~/.collective-wisdom/scripts/cos_route.py <PREFIX>-N <caller> --thread <this thread's id>` and act on its last line. The callers:

- `approve-spec` (`approve N` on a spec): run the models.md § Models switch (`t3_thread_configure` on the child that will receive the relay) immediately before the send, whether the send is immediate or comes later from the queue; skip it when a continuation starts.
- `approve-merge` (`approve N` on a merge), `changes` (`changes N`), `answer` (how to proceed on a blocked ticket, or an answer to a pending request), `resume` (tickets stopped by the user), `rate-limit` (cleared, for tickets blocked by it).
- `reviewer-changes` (review.md § Review check, `changes` line) and `head-moved` (that file's `moved` line, or the head check below).
- `conflict-keep`, `conflict-stand`, `conflict-withdraw`: the head check, `conflict: yes` in an approval request, or a `BLOCKED:` merge child.

The script prints the `stage` op to apply (fill in `status`), then:

- `route: send <lane>`: `t3_thread_send` the relay to the ticket's child, then apply the `stage` op, which clears `pendingRelay`, `approvalItemId` and `queuedAt`, saved before the next line. Copy a `moving:` line under Moving.
- `route: queue <lane>`: don't send. Apply the `stage` op (to `<lane>-queued`) with `pendingRelay` and, for a user spec approval, `approvalItemId` in `set`.
- `route: continuation <lane>`: continuation.md § Continuation child, in place of the send. If it falls back to sending to the old child, copy the `fallback:` line under Moving, and apply the lane's stage op with the `set:` line's keys.
- `route: no <why>` (exit 1): the caller doesn't apply from that stage; don't send. Exit 2 (`route: cannot <what>`): don't send, and tell the user under Needs you.

The stuck-check restart is not a caller (the child still holds its slot), and neither are the send-backs in approvals.md § Approval requests, which happen in the turn the child reported. A queued relay stores the relay text only; any model switch happens at send time, just before the send.

Every spec approval relay from the user has a second line, `Approval in thread: <thread id>`: the thread where the user wrote the approval (your own thread ID for an immediate one; the stored line for a queued one). The spec approval relay:

```
CHIEF OF STAFF: the user approved the spec: "<their words>". Continue to the build stage.
Approval in thread: <thread id>
```

An auto-approved spec (approvals.md § Auto-approval) is relayed the same way, with no user message to prove it, so its relay has no thread line and its queue entry has no `approvalItemId`:

```
CHIEF OF STAFF: auto-approved the spec under `<tolerance>` (Risk: <Level> (<reason>)). Continue to the build stage.
```

Under a No Hands run `<tolerance>` is `No Hands` everywhere in this section, and the spec relay is `CHIEF OF STAFF: auto-approved the spec under No Hands. Continue to the build stage.`, with no `Risk:` part.

A queued spec approval stores both lines in `pendingRelay`, and the item id of the user's message in `approvalItemId`. A merge approval relay has no thread line and stores no `approvalItemId`: `cos_approve_pr.py` checks the user's message before the relay is sent or queued, and the relay names the head it checked. A queued merge approval keeps its place.

Before sending a queued spec approval, run `python3 ~/.collective-wisdom/scripts/cos_user_check.py item <thread in its Approval in thread: line> <approvalItemId>` with the quoted words on stdin (quoted heredoc). Exit 0 passes. Exit 1 (`reject: …`): don't send: drop the queued relay, `comment` `Approval withdrawn at <time>: the approval message could not be verified.`, and report it under Needs you. Exit 2: `t3_thread_read` that thread with `itemId: <approvalItemId>` and `maxCharsPerItem: 500`; `createdBy` must be `"user"` and the text must contain the quoted words; add one Cleanup line, `User check script unavailable; used thread read`. An approval sent at once uses the item id of the message you read when you verified the command (commands.md § Commands).

A queued auto-approved relay skips that check. Instead, run `python3 ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec` (a spec, with the ticket still in the queue) or `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto` (a merge) again just before it is sent. Anything but exit 0 means don't send: drop the relay, `comment` `Approval withdrawn at <time>: the auto-approval no longer holds.`, set the stage back to `awaiting-build` or `awaiting-merge`, and ask the user as usual. When a queued auto spec relay passes and is sent, first post `<PREFIX>-N: Auto-approved under <tolerance>; the build has started.` in the sending thread; the child reads that thread for the notice (ship-loop § Approvals).

**Continuation child.** When a relay (at once or from the queue) is about to go to a ticket whose `parentThreadId` is known and is not `chiefThreadId`, read continuation.md § Continuation child. It may start a new child under this thread instead of sending (an approval or `changes N` after `awaiting-*`, or any other relay when the old child's worktree check passes).

**Verify a merge approval**, after the head check and before the relay is sent or queued: `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N`. Exit 0 (`verified`): build the merge relay (only after this exit 0 in this run) and send or queue it. Exit 1 or 2: don't send or queue, keep the stage at `awaiting-merge`, and tell the user under Needs you with the script's last line, adding that they can reply `approve N` again once it is fixed. Exit 2 from the message store never falls back to a thread read.

**Verify an auto-approved merge**, after the head check and before the relay is sent or queued: `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto`. It reads no user message. Exit 0 (`auto-approved`): post the merge block as a notice (approvals.md § Auto-approval) and send or queue the relay. Exit 1 or 2: don't send or queue, keep the stage at `awaiting-merge`, and ask the user with the normal approval request, adding the script's last line under Needs you.

**Head check for a merge approval**, before it is sent or queued and again before a queued one is sent: `python3 ~/.collective-wisdom/scripts/cos_head_check.py <PREFIX>-N`. It prints the relay to send (the conflict relay names the verified head and is never sent for any other head), then a last line:

- `head-check: ok`: go on.
- `head-check: moved <old> <new>`: the head moved after the reviews the user saw. Don't send, and drop the approval if it was queued. `comment` `Approval withdrawn at <time>: the PR head moved.`, tell the user under Needs you, and send the printed relay (`head-moved`).
- `head-check: conflict keep`: keep the approval (verified at this head) and send the printed relay (`conflict-keep`).
- `head-check: conflict stand`: no approval exists, reviews stand: send the printed relay (`conflict-stand`). It comes from `--no-approval` callers and a `BLOCKED:` merge child whose state says `noApproval`.
- `head-check: conflict withdraw`: `comment` `Approval withdrawn at <time>: the PR conflicts with <target>.`, tell the user under Needs you, and send the printed relay (`conflict-withdraw`).
- Exit 2 (`head-check: cannot <what>`): don't send, and tell the user under Needs you.

The merge relay names the head:

```
CHIEF OF STAFF: the user approved the merge of PR #X at head <short SHA>: "<their words>".
```

After `--auto` exit 0 the relay says so instead, and still names the head:

```
CHIEF OF STAFF: auto-approved the merge of PR #X at head <short SHA> under `<tolerance>` (Risk: <Level> (<reason>)).
```

The ticket comment on an approval: approvals.md § Ticket comment on approval.
