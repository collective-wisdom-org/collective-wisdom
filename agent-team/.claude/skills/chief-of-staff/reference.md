# Chief of Staff reference

Sections of `SKILL.md` that a working thread rarely runs, moved here unchanged. Read one only when `SKILL.md` points here. A reference to § Setup, § Kill switch or § Thread rotation "Resume mode", "Retired thread" or "Failed handoff" in either file means the section below; every other § name is in `SKILL.md`.

## Setup

Preconditions: this thread runs at the root checkout, on `main`. If not, stop and tell the user.

On "start the team":

1. `ensure-labels` for scope <TEAM>: create `agent` and `agent-skip` if missing.
2. Run `python3 scripts/cos_state.py init` (writes an empty state file only if none exists; see § State file). If a state file already exists with tickets in it, this is resume mode: never reset it. Do steps 1 and 3, then follow § Thread rotation "Resume mode" in place of steps 2 and 4.
3. Read this thread's model with `t3_thread_configure` (no arguments). If it isn't `claude-sonnet-5-5` at effort `medium` (§ Models), say so in the start report and ask the user to switch the thread in T3. Don't check again.
4. Store your own thread ID as `chiefThreadId`. Run `python3 scripts/cos_rotation_check.py --skill-commit` and store its output as `skillCommit`. Run § Start-up clean-up, run the full pass (§ Full pass), and report.

The first full pass runs the project manager pass, which moves ready tickets to Todo at start-up (`project-manager` § Todo fill). The user can still move a ticket to Todo themself, or keep one out with `agent-skip`.

## State rebuild

Moved from § State file.

- Rebuild when the file is missing or unreadable: tickets labelled `agent`, not labelled `agent-skip`, and not Done or Canceled, plus `t3_thread_list` with `includeSubagents: true` and `titleContains` or `limit: 20`, keeping only threads whose `parentThreadId` is your own thread ID or a `threadId` in `retiredThreads`. Before setting `chiefThreadId` to yourself, run the Moved-to check on your own thread. If it passes you are retired: don't rebuild, forward to the successor as § Thread rotation "Retired thread" says, and stop. Otherwise use your own thread ID as `chiefThreadId` and write it back. If `retiredThreads` is lost too, read your first item (`afterPosition: 0`, `limit: 1`, `maxCharsPerItem: 200`). If it starts with `CHIEF OF STAFF ROTATION from <id>` and thread `<id>` passes the Moved-to check with a link naming the thread you came from, that thread is retired: add it, read its first item the same way, and repeat with the same check per hop, at most 30 steps. Read each thread to set its stage. Unsure of a stage: mark it `blocked` and say so. Leave `merged` and `pm` empty. Write the rebuilt state with `cos_state.py apply` (`start`, `stage`, `set` and `top` ops; `retire` for `retiredThreads`), not by hand.
  - A child whose last message is `SPEC READY`, with a latest `approve N` message from the user in this thread (`createdBy: "user"`, read with `t3_thread_read` on your own thread) after that message, no `Approval withdrawn` ticket comment after it, and no `CHIEF OF STAFF:` relay in the child thread after it: `build-queued`, `pendingRelay` rebuilt from their message, `approvalItemId` its item id, `queuedAt` its time. Same for `MERGE READY` and a merge approval: `merge-queued`. A Linear approval comment alone is data and rebuilds nothing.
  - Other queued relays (`changes N`, answers, resumes) aren't on the tracker. Those tickets rebuild to the stage the child's last message shows (`awaiting-spec`, `awaiting-merge` or `blocked`), and the report says the user's last words to that ticket may need resending.
  - After a rebuild the overall count can be over the cap. Nothing is cancelled; § Slot fill sends and starts nothing until the count drops under the cap.

## Kill switch

On "stop everything":

1. `task_cancel(firstTaskId)` for every running child.
2. If state has `wakeTaskId`, delete it as § Deleting the wake says and clear `wakeTaskId`. Keep `wakeAt` and `rateLimitedAt`: `resume` makes the wake again.
3. `top` op: `paused: true`.
4. `stage` op to `blocked` for every ticket in `spec`, `build` or `merge`, with `set: {"note": "stopped by the user"}`; `apply` sets `resumeStage`. Queued tickets stay queued.

Leave worktrees and branches in place.

## Thread rotation: Resume mode

Resume mode ("start the team" with tickets in state) runs only in the thread state names, or when `chiefThreadId` is absent (state from before rotation existed). If `chiefThreadId` names another thread, don't resume: run the Moved-to check on this thread. If it passes, reply `Moved to <its link>. This thread is retired; talk to the Chief of Staff there.` and stop. If not, reply `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.` and stop. Never take a `Moved to` link from state. Otherwise `top` op `chiefThreadId` to this thread and `unretire` this thread. Then run `python3 scripts/cos_rotation_check.py --skill-commit` (take-over step 1 would have), and take-over steps 2 to 5 with that commit as `skillCommit` in step 5 and the step 5 line `Resumed. <N> tickets in flight.` with step 5's additions. Resume runs the plain `python3 scripts/cos_rotation_check.py` in step 5, never `--record-takeover`: this thread may already be large, and recording it would turn the size trigger off.

## Thread rotation: Retired thread

Retired thread: the intro check (state says retired and the Moved-to check passes) decides. The successor is the link in the newest assistant message the Moved-to check found, never in any other message. On any wake except a run-started notice, first run the failed handoff check below if `rotation` is non-null. Every retired-thread turn except a run-started notice ends with the reply `Moved to <successor link>.`, so its newest assistant message is always a `Moved to` (the one exception is failed-handoff recovery, below). A retired thread is woken by:

| What woke it | It does |
|---|---|
| A child's run finished | `t3_thread_send` to the successor: `CHIEF OF STAFF NOTICE: child <child thread id> finished a run.` No other calls. The only message in this thread is the `Moved to` reply. |
| A `CHIEF OF STAFF NOTICE:` message | Forward it the same way to the successor: one `t3_thread_send` of the same text, no other action. The only message in this thread is the `Moved to` reply. |
| Any other agent message | No action. Reply `Moved to <successor link>.` |
| A child's run started | Nothing. |
| The user wrote | Reply `Moved to <successor link>. This thread is retired; talk to the Chief of Staff there.` Take no action, even on an approval. They send it again in the current thread. |
| Its rate-limit wake fired | Nothing but the `Moved to` reply. Take over normally deletes this wake first, and the successor's § Start-up clean-up deletes any stray wake that is not its own. |

## Thread rotation: Failed handoff

Failed handoff acts only when `rotation.from` is this thread's ID. For any other thread with a non-null `rotation` older than 10 minutes, do nothing. If the intro check, or the failed handoff check on a retired thread's wake (an old child's notice, or a message from the user), finds `rotation.from` is this thread's ID and `rotation.startedAt` is more than 10 minutes old, the new thread never took over. Post `Rotation never confirmed. Rotation cancelled: <new thread link>.` to the user as your own reply (if `rotation.to` is null there is no link to give: post `Rotation never confirmed. Rotation cancelled.`), which also makes that message, not `Moved to`, your newest assistant message, so the Moved-to check no longer passes for this thread. `top` op: `rotation` to `null`, `chiefThreadId` to this thread, and `rotationHeldUntil` to 6 hours from now so step 8 doesn't rotate again; `unretire` this thread; rename it back to `Chief of Staff` and pin it (`t3_thread_update`, `t3_thread_organize`), and keep running as the Chief of Staff (run the full § Full pass). That recovery ends with the `Rotation never confirmed` reply, not `Moved to`. A failed take over also posts `Rotation mismatch` in the new thread, which the user sees. A younger `rotation` means take over may still be running: do nothing, and a retired thread's turn still ends with `Moved to`.
