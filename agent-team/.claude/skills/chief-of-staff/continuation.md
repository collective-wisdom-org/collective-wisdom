# Chief of Staff: continuation child

Read when a relay is about to go to a ticket whose `parentThreadId` is known and is not `chiefThreadId`.

## Continuation child

When SKILL.md § Send or queue is about to send a relay (at once or from the queue) to a ticket whose `parentThreadId` is known and is not `chiefThreadId`, it may start a new child under this thread instead of sending. There are two cases.

*Approval or `changes N`.* The relay is the user's approval (`CHIEF OF STAFF: the user approved`), an auto-approval (`CHIEF OF STAFF: auto-approved`) or `changes N` (`CHIEF OF STAFF: the user asked for changes`) for a ticket that was in `awaiting-spec` or `awaiting-merge` (the child has pushed everything and is idle; a queued relay of this kind is told apart by its first words), **and** the relay has no `Approval in thread:` line or that line names this thread: start a new child under this thread instead of sending. A queued spec approval written in an older thread (the line names another thread) is sent to the old child as before.

*Any other relay* (a restart, an answer to a blocked child, `resume`, a rate-limit continue, even when queued). The old child may hold unpushed work, so first check that it holds none:

1. `t3_thread_read` the old child once (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`) for `recentRuns[0].status` and `worktreePath`, and `t3_pending_request` `list` on it. A `running` run, a pending request, a failed read or call, or no `worktreePath`: send to the old child as before. A run that is still open can change its worktree, and the request would be left hanging. (An answer to a pending request is always this case.)
2. `python3 scripts/cos_worktree_check.py <PREFIX>-N -- '<worktreePath>'` (from the root checkout). Exit 0 (`safe`): start a continuation child as the steps below say, with this relay as the task's last block. Exit 1 or 2: send to the old child as before, and add one Cleanup line, `<PREFIX>-N kept its old child: <the script's line>`.

The steps below apply to both cases.

- Before writing the template, run `python3 scripts/cos_handoff.py <PREFIX>-N`. It checks `branch`, `specPath`, `specSha`, `stage` and `pr` (all from the child's own report) and prints a `HANDOFF` block built from state and GitHub. Exit 1 (`reject: <field> <value>`): mark the ticket `blocked`, quote the value to the user, and start nothing. Exit 2 with the line `cos_handoff: cannot read PR #N` (the checks above passed, only GitHub failed): start the child with the `Spec: … PR: …` line of the template as it was, and add one Cleanup line, `Handoff block unavailable for <PREFIX>-N`. Exit 2 with any other line (`bad ticket`, `no state file`, `no such ticket`, `unreadable state file`): the values were not checked, so start nothing, mark the ticket `blocked` and quote the line to the user. Otherwise the block replaces that line in the template, as printed.
- The merge head check and the queued spec approval re-read (SKILL.md § Send or queue) run first, as for any send. Then `delegate_task` as in SKILL.md § Readiness check and start, on the lane's model (Opus 5.5 at effort medium for the spec lane, Sonnet 5.5 at effort high for build and merge; SKILL.md § Models), with the template below. The relay goes into the task as its last block. The SKILL.md § Models switch is skipped: the new child starts on the lane's model.
- Save the new `firstTaskId` and `childThreadId`, set `parentThreadId` to this thread's ID and `lastPosition` to 0, and set the lane's active stage and `status` as for any send. The old child stays idle and is never sent to again. Its worktree and branch stay.
- Report under Moving: `<PREFIX>-N moved to a new child (old one under a retired thread)`.

These still go to the old child: a running child (it can't be moved), a child with a pending request (its run is open), and any child whose worktree check fails (unpushed or uncommitted work, or a worktree the check can't read). Its notices still go through the old thread's forwarding, and the sweep's parent check (SKILL.md § Sweep) full-reads it in case a forward is lost.

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

The old child's worktree stays idle with the branch checked out; `--ignore-other-worktrees` lets the new one take the branch.

The task's Chief of Staff thread is this thread, never the relay's approval-thread line. The relay is the task's last block, and its approval thread is this thread (the condition above) or has no line, so the child's check of the user's message is direct (spec approvals only). Every later Chief of Staff thread descends from this one, so a later spec approval passes the chain check as today. A merge approval needs no thread check: its proof is the relay the Chief of Staff sends after `scripts/cos_approve_pr.py` verified the user's `approve N` or passed with `--auto`, and the child reads no thread for it.
