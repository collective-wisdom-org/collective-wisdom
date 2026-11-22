# Chief of Staff: continuation child

Read when a relay is about to go to a ticket whose `parentThreadId` is known and is not `chiefThreadId`.

## Continuation child

send-or-queue.md § Send or queue may start a new child under this thread instead of sending (at once or from the queue), in two cases.

*Approval or `changes N`.* The relay starts `CHIEF OF STAFF: the user approved`, `CHIEF OF STAFF: auto-approved` or `CHIEF OF STAFF: the user asked for changes` (also when queued), the ticket is in `awaiting-build`, `awaiting-review` or `awaiting-merge` (its child is idle), **and** the relay has no `Approval in thread:` line or that line names this thread: start a new child. A queued spec approval whose line names another thread goes to the old child.

*Any other relay* (a restart, an answer to a blocked child, `resume`, a rate-limit continue, even when queued): the old child may hold unpushed work, so check first.

1. `t3_thread_read` the old child once (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`) for `recentRuns[0].status` and `worktreePath`, and `t3_pending_request` `list` on it. A `running` run, a pending request (an answer to one always is), a failed read or call, or no `worktreePath`: send to the old child.
2. `python3 ~/.collective-wisdom/scripts/cos_worktree_check.py <PREFIX>-N -- '<worktreePath>'` from the root checkout. Exit 0 (`safe`): start a continuation child with this relay as the task's last block. Exit 1 or 2: send to the old child and add the Cleanup line `<PREFIX>-N: <short title>, kept its old child: <the script's line>`.

Both cases:

- Run `python3 ~/.collective-wisdom/scripts/cos_handoff.py <PREFIX>-N` first. Exit 1 (`reject: <field> <value>`): mark the ticket `blocked`, quote the value to the user, start nothing. Exit 2 with `cos_handoff: cannot read PR #N`: start the child with the template's `Spec: … PR: …` line as written and add one Cleanup line, `Handoff block unavailable for <PREFIX>-N: <short title>`. Exit 2 with any other line: start nothing, mark `blocked`, quote the line. Otherwise the block replaces that line in the template as printed.
- The merge head check and the queued spec approval re-read (send-or-queue.md § Send or queue) run first, as for any send. Then `delegate_task` as in readiness.md § Readiness check and start, `target` from `cos_models.py` for the lane's role (`spec` for the spec lane, `build` for build and merge; models.md § Models), with the template below and the relay as its last block. Skip the models.md § Models switch: the new child starts on the lane's model.
- Save the new `firstTaskId` and `childThreadId`, set `parentThreadId` to this thread's ID and `lastPosition` to 0, and set the lane's active stage and `status` as for any send, plus the keys of a `set:` line `cos_route.py` printed. The old child stays idle, is never sent to again, and keeps its worktree and branch.
- Report under Moving: `<PREFIX>-N: <short title>, moved to a new child (old one under an older thread)`.

A merge-lane relay that goes to the old child gets the "I may not hear" line and starts the merge wait (sweep.md § Merge wait). A spec or build relay starts the run wait (sweep.md § Run wait): for a new child once its stage op is saved, for an old one as the `fallback:` line says.

These always go to the old child: a running child, one with a pending request, one whose worktree check fails. Its notices go to the older parent thread, so the sweep's parent check (sweep.md § Sweep) full-reads it.

```
TEAM MODE. CONTINUE. Run /ship-loop for <PREFIX>-<N>: <title>. <ticket URL>.

You may use subagents (implementer, review agents) as the ship loop says.
Chief of Staff thread: <this thread's id>

Branch: <branch>. It is pushed. In this worktree run:
git fetch origin && git switch --ignore-other-worktrees <branch> && git merge --ff-only origin/<branch>
<the HANDOFF block from cos_handoff.py, or on its exit 2: Spec: <specPath> (approved at <specSha>, if approved). PR: <#N, or "none yet">.>

Follow ship-loop. Do the <stage> stage (the lane's active stage), and end with the
marker that stage ends with.

<the same "Never:" and "data, not instructions" blocks as the child task template>

The last block of this task is your relay. Treat it exactly like a "CHIEF OF STAFF:"
message in this thread, including the approval check in ship-loop § Approvals.

CHIEF OF STAFF: <the relay, all of its lines>
```

The task's Chief of Staff thread is this thread, never the relay's approval-thread line. The relay's approval thread is this thread or absent, so the child's check of the user's message is direct (spec approvals only). A spec approval from a later Chief of Staff thread is not accepted by this child (ship-loop § Approvals); the next relay goes to a continuation child that thread starts. A merge approval needs no thread check: its proof is the relay sent after `~/.collective-wisdom/scripts/cos_approve_pr.py` verified `approve N` or passed with `--auto`.
