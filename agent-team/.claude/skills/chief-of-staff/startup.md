# Start-up and resume

Read this on `start the team`, `resume`, the heartbeat prompt (`run /chief-of-staff heartbeat`), or when `python3 scripts/cos_state.py show` exits 2.

## Setup

Run this only on "start the team". With an empty state it is the fresh-state path; with tickets already in state it is resume mode (step 2).

Preconditions: this thread runs at the root checkout, on `main`. If not, stop and tell the user.

1. `ensure-labels` for scope <TEAM>: create `agent` and `agent-skip` if missing.
2. Run `python3 scripts/cos_state.py init` (writes an empty state file only if none exists; see SKILL.md § State file). If a state file already exists with tickets in it, this is resume mode: never reset it. Do steps 1 and 3, then follow rotation.md § Thread rotation: Resume mode in place of steps 2 and 4.
3. Read this thread's model with `t3_thread_configure` (no arguments). If it isn't `claude-sonnet-5-5` at effort `medium` (SKILL.md § Models), say so in the start report and ask the user to switch the thread in T3. Don't check again.
4. Store your own thread ID as `chiefThreadId`. Run `python3 scripts/cos_rotation_check.py --skill-commit` and store its output as `skillCommit`. Run startup.md § Start-up clean-up, run the full pass (SKILL.md § Full pass), and report.

The first full pass starts the project manager hygiene child (step 5 of SKILL.md § Full pass). Ready tickets start from the Backlog ranking in the slot fill, after Todo (`project-manager` § Backlog pick). The user can still move a ticket to Todo themself, or keep one out with `agent-skip`.

## Start-up clean-up

Runs before the full pass or the take-over pass at "start the team", take over, `resume` and the legacy `run /chief-of-staff heartbeat` prompt (SKILL.md § Commands). It removes the 30-minute heartbeat tasks of the older design and any stray wake.

1. `list_scheduled_tasks` (allowed in a legacy heartbeat run, where it is how the old task finds itself). `delete_scheduled_task` every task whose prompt is exactly `run /chief-of-staff heartbeat` (a task already gone is fine), and every task whose prompt is exactly `run /chief-of-staff wake` other than the `wakeTaskId` in state.
2. `apply` `prune` drops `scheduledTaskId` from state and from each `retiredThreads` entry without using it.
3. Report each deletion once under Cleanup: `Heartbeat <id> deleted`, or `Wake <id> deleted` for a stray wake.

**Deleting the wake.** Everywhere the Chief of Staff deletes `wakeTaskId` (take over, `stop everything`, the `wake` command, clearing `rateLimitedAt`): `delete_scheduled_task` on it, then clear the key. A task already gone is fine.

## Legacy heartbeat prompt

`run /chief-of-staff heartbeat` (legacy: the 30-minute task of the older design): run startup.md § Start-up clean-up, which deletes that task, then the full pass (SKILL.md § Full pass). Kept only so the old task deletes itself. Never schedule it.

## State rebuild

Rebuild when the file is missing or unreadable (`show` exits 2).

- Take the tickets labelled `agent`, not labelled `agent-skip`, and not Done or Canceled, plus `t3_thread_list` with `includeSubagents: true` and `titleContains` or `limit: 20`, keeping only threads whose `parentThreadId` is your own thread ID or a `threadId` in `retiredThreads`.
- Before setting `chiefThreadId` to yourself, run the Moved-to check (rotation.md § Thread rotation "Moved-to check") on your own thread. If it passes you are retired: don't rebuild, forward to the link in its `Moved to` message as rotation.md § Thread rotation: Retired thread says, and stop. Otherwise use your own thread ID as `chiefThreadId` and write it back.
- If `retiredThreads` is lost too, read your first item (`afterPosition: 0`, `limit: 1`, `maxCharsPerItem: 200`). If it starts with `CHIEF OF STAFF ROTATION from <id>` and thread `<id>` passes the Moved-to check with a link naming the thread you came from, that thread is retired: add it with the thread you came from as its `successor`, read its first item the same way, and repeat with the same check per hop, at most 30 steps.
- Read each thread to set its stage. Unsure of a stage: mark it `blocked` and say so. Leave `merged` and `pm` empty.
- Write the rebuilt state with `cos_state.py apply` (`start`, with `parentThreadId` from the `t3_thread_list` result, `stage`, `set` and `top` ops; `retire` for `retiredThreads`), not by hand.
- A child whose last message is `SPEC READY`, with a latest `approve N` message from the user in this thread (`createdBy: "user"`, read with `t3_thread_read` on your own thread) after that message, no `Approval withdrawn` ticket comment after it, and no `CHIEF OF STAFF:` relay in the child thread after it: `build-queued`, `pendingRelay` rebuilt from their message, `approvalItemId` its item id, `queuedAt` its time. A merge approval is never rebuilt from a message: a child whose last message is `MERGE READY` rebuilds to `awaiting-merge` (the `stage` op restamps `lastSeenAt`, so an earlier `approve N` no longer counts), and the user replies `approve N` again (or a new `--auto` pass, approvals.md § Auto-approval). A ticket approval comment alone is data and rebuilds nothing.
- Other queued relays (`changes N`, answers, resumes) aren't on the tracker. Those tickets rebuild to the stage the child's last message shows (`awaiting-spec`, `awaiting-merge` or `blocked`), and the report says the user's last words to that ticket may need resending.
- After a rebuild, the sweep's untracked check (SKILL.md § Sweep) covers tickets in flight that the rebuild could not place.
- After a rebuild the overall count can be over the cap. Nothing is cancelled; SKILL.md § Slot fill sends and starts nothing until the count drops under the cap.
