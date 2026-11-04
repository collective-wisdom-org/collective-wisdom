# Chief of Staff: handoff and rotation

Read this when the rotation check says `rotate:`, on `take over`, when state says this thread is retired, or when `rotation` is non-null in state.

## Thread rotation

As the last Bash call of every turn that made a tool call, run this from the root checkout:

```bash
python3 scripts/cos_rotation_check.py
```

The only turn that skips it is a run-started notice, which makes no tool calls. A retired thread never runs it, since it would claim `chiefSessionId`. A Stop hook (`.claude/settings.json`) runs the same script and sends the turn back when it says `rotate:`, so the check still happens if you forget it.

It prints one line, `ok ...` or `rotate: <reason>`, and exits 0. It applies this table (the size cap is `SIZE_CAP` and the quiet windows are `QUIET_RELAY_MIN` and `QUIET_ROTATED_MIN` in the script; change doc and script together):

| Trigger | Threshold |
|---|---|
| Size | context is 220k or more (ignores the quiet-turn rule) |
| Skill change | the current skill commit differs from `skillCommit` in state (only on `main`) **and** the turn is quiet (below). A `null` `skillCommit` prints `ok; set skillCommit <sha>`, save it and don't rotate |

A turn is quiet when no ticket is in a `*-queued` stage, `lastRelayAt` is absent or 10 minutes old or more, and the newest `retiredAt` in `retiredThreads` is 60 minutes old or more (or there is none). A skill change on a turn that isn't quiet prints `ok (skill change waits: queued <PREFIX>-N)`, `ok (skill change waits: relay <N>m ago)` or `ok (skill change waits: rotated <N>m ago)`, the first that applies. Do nothing: the skill commit stays different, so the first quiet turn rotates. If the size trigger also fires, it rotates now.

It holds (prints `ok (held: ...)`) while `paused` is set, while `rotation` is set, and while `rotationHeldUntil` is in the future. Never rotate in the middle of a command. It also saves `chiefSessionId` in state.

On `rotate:`, run the handoff below. If the script exits 2 (`rotation-check: cannot read <what>`), fall back to the item count: `t3_thread_read` on your own thread with `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`, read `itemCount`, and rotate at 240 or more. Add one Cleanup line: `Context size unreadable; used item count`. Item count is used only for this fallback.

A take-over turn that ends above 90k adds a Cleanup line, `Take-over ended at <N>k; working set is larger than it should be`. If it ended at or above the size cap, the script turns the size trigger off for this thread (`takeoverContext`) and prints `ok (size trigger off: take-over ended at <N>k)`, so the thread does not rotate again and again.

**Archiving.** At the end of a turn that ran a full pass, a slot fill or the take-over pass, before the rotation check, archive only a prefix of `retiredThreads`, oldest first, among entries without `archivedAt`. An entry may be archived only if no ticket has it or any older entry as `parentThreadId`, and every ticket's `parentThreadId` is known; stop at the first entry that fails. `python3 scripts/cos_parent_check.py --thread <this thread's id>` applies that rule to state. Archive only the threads on its `archive` lines, in order. `t3_thread_organize` with `archive`, set `archivedAt` to now, then at once `t3_thread_read` it (`limit: 1`, `maxCharsPerItem: 1`). If that read fails, `unarchive` it (`t3_thread_organize`), clear `archivedAt`, archive nothing more, and report once under Cleanup. Its last message is already `Moved to …`.

**Moved-to check** on a thread X (the legacy successor fallback in the SKILL.md intro, take over, the rebuild and the children's chain check use it): `t3_thread_read` X with `limit: 1`, `maxCharsPerItem: 1` for `itemCount`, then read from `afterPosition: max(0, itemCount - 8)` with `limit: 8`, `maxCharsPerItem: 300`, `view: messages`. Count only items with `type: "assistant_message"`, `creationSource: "provider"`, `visibility: "local"` and `sourceThreadId` equal to X's id. If none of the 8 counts, step back another 8, until one does or you reach the thread start. It passes when the newest counted item starts with `Moved to`. Its link carries the successor's thread id. Anything else does not count, such as a `t3_thread_send` message or one copied in from another thread.

Every message a retired thread posts starts with `Moved to <successor link>.`, so its newest assistant message always passes. Each retired thread points to its own successor (A to B, B to C), not to the current Chief of Staff. Nobody writes a message starting `Moved to` except the handoff line and retired-thread replies.

Handoff, in the old thread:

1. Set `rotation` to `{from: <own id>, to: null, startedAt: now}`. Save state.
2. `t3_thread_launch` with `title: "Chief of Staff"`, `workspaceStrategy: {type: "root"}`, `modelSelection: {instanceId: "claudeAgent", model: "claude-sonnet-5-5", options: {effort: "medium"}}` (SKILL.md § Models), and this message:

   ```
   CHIEF OF STAFF ROTATION from <old thread id>.
   Run /chief-of-staff take over.
   ```

3. Set `rotation.to` to the new thread ID. Save state.
4. `t3_thread_update` rename to `Chief of Staff (old)`, `t3_thread_organize` unpin.
5. In one `apply`, set `chiefThreadId` to the new thread ID and `chiefSessionId` to `null` (`top` op, so this thread's Stop hook goes quiet), and `retire` the old thread's ID with `successor` set to the new thread ID. Save state. This is the last tool call.
6. End the turn with `Moved to <new thread link>. Talk to me there.` as your own reply text, so it is an assistant message. Never `t3_thread_send` it: that makes it a `type: "user_message"` with `creationSource: "mcp"`, which the Moved-to check never counts. The link contains the new thread's id.

A turn that dies between steps 5 and 6 leaves state saying retired with no `Moved to` message. The SKILL.md intro covers it (rotation.md § Thread rotation: Failed handoff).

Take over, in the new thread (the `take over` command):

1. Load this skill, run `python3 scripts/cos_rotation_check.py --skill-commit` for `skillCommit`, and read state with `python3 scripts/cos_state.py show`. Never print `state.json` and never call `orchestrator_capabilities` here. Confirm the `take over` message is this thread's first item (`afterPosition: 0`, `limit: 1`) and that the Moved-to check on this thread does not pass (a retired thread never takes over). Confirm `rotation.to` is this thread and `rotation.from` matches the id in the launch message. Then run the Moved-to check on `rotation.from`: it must pass and its link must name this thread. If `rotation.from` matches but `rotation.to` is null, or the check does not pass yet, the old thread has not finished: wait (`sleep 10` in Bash) and re-read state and re-check, up to 5 times, before calling it a mismatch. On a state mismatch, post `Rotation mismatch: <one line>` and stop. If the check never passes, post `Rotation mismatch: no Moved to message in <old link>` and stop. Schedule nothing.
2. If state has `wakeTaskId`, delete it as startup.md § Deleting the wake says (it is bound to the old thread) and clear `wakeTaskId` (keep `wakeAt`). Step 4 makes a new wake in this thread if a rate limit still needs one.
3. `t3_thread_organize` pin this thread. Set `rotation` to `null`. In `take over` only, not resume mode, then post `Taking over from <old thread link>. Checking the tickets in flight; a summary follows.` as your own reply text (an assistant message, never `t3_thread_send`) and go on to step 4 in the same turn. Every `Rotation mismatch` stop comes before this line.
4. Run the lean take-over pass. It also serves `resume` and resume mode; only "start the team" with an empty state runs the full pass.
   1. startup.md § Start-up clean-up.
   2. For each ticket in `spec`, `build` or `merge`, the idle-check read (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`). A child that is running and idle more than 45 minutes, or whose `updatedAt` is later than its `lastSeenAt`, or whose ticket has no `status` line, gets the full read and steps 2 to 4 of SKILL.md § Full pass. Every other child costs that one small read. This picks up anything that finished during the handoff. Then run the sweep (SKILL.md § Sweep), before 4.4. Every ticket on its `read in full:` line gets the full read and steps 2 to 4 of SKILL.md § Full pass, whatever the small read showed. A part that didn't run gets the fallback in SKILL.md § Sweep.
   3. Queued, awaiting and blocked tickets are not read; their `status` line is enough. A pending `rateLimitedAt` still gets its wake or its clearing as SKILL.md § Full pass step 4 says.
   4. Run SKILL.md § Slot fill in full: the gate, then step 2 (merge, build, then spec: `spec-queued`, Todo, then the Backlog pick with its ranking when nothing ranked is `ready`). The hygiene child runs on the next full pass that needs it.
5. Set `skillCommit` to the commit from step 1 and save state. Then run `python3 scripts/cos_rotation_check.py --record-takeover` as the last Bash call: it saves `takeoverContext` with this thread's context size and prints the rotation check line. Post one line: `Take-over done. <N> tickets in flight. Take-over context <K>k.` (`<K>` is the `take-over context=<K>k` the script printed). When the sweep's parent check printed any `full` or `idle` line, add `<M> still under an older thread: <PREFIX>-125, <PREFIX>-127.` to that line. When a lane is free and nothing started, add `Filling stopped: <reason>.` (the reasons in SKILL.md § Report format). Add a report only if step 4 found something.

If the user writes in a thread that is `rotation.to` while `rotation` is non-null, take over never ran (this thread runs one turn at a time). Within 10 minutes of `rotation.startedAt`, run take over before their command. After 10 minutes the old thread's failed handoff may be recovering, so don't take over: reply `Rotation never confirmed; write in <old thread link>.` Re-run step 1's check on the old thread just before step 3, and stop with `Rotation mismatch` if `rotation` changed or the check no longer passes.

## Thread rotation: Resume mode

Resume mode ("start the team" with tickets in state) runs only in the thread state names, or when `chiefThreadId` is absent (state from before rotation existed). If `chiefThreadId` names another thread, don't resume. If this thread is in `retiredThreads`, reply `Moved to <its successor link>. This thread is retired; talk to the Chief of Staff there.` (the successor as the SKILL.md intro gives it; if the intro names none, take no action and reply with its no-successor line) and stop. If not, reply `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.` and stop. Otherwise `top` op `chiefThreadId` to this thread and `unretire` this thread. Then run `python3 scripts/cos_rotation_check.py --skill-commit` (take-over step 1 would have), and take-over steps 2 to 5 with that commit as `skillCommit` in step 5 and the step 5 line `Resumed. <N> tickets in flight.` with step 5's additions. Resume runs the plain `python3 scripts/cos_rotation_check.py` in step 5, never `--record-takeover`: this thread may already be large, and recording it would turn the size trigger off.

## Thread rotation: Retired thread

Retired thread: the SKILL.md intro decides. The successor is the one the intro gives: the `successor` in this thread's `retiredThreads` entry, or for an entry without one the link in the newest assistant message the Moved-to check found. On any wake except a run-started notice, first run the failed handoff check (rotation.md § Thread rotation: Failed handoff) if `rotation` is non-null. Every retired-thread turn except a run-started notice ends with the reply `Moved to <successor link>.`, so its newest assistant message is always a `Moved to` (the one exception is failed-handoff recovery). A retired thread is woken by:

| What woke it | It does |
|---|---|
| A child's run finished | `t3_thread_send` to the successor: `CHIEF OF STAFF NOTICE: child <child thread id> finished a run.` No other calls. The only message in this thread is the `Moved to` reply. |
| A `CHIEF OF STAFF NOTICE:` message | Forward it the same way to the successor: one `t3_thread_send` of the same text, no other action. The only message in this thread is the `Moved to` reply. |
| A `CHIEF OF STAFF REQUEST` or `CHIEF OF STAFF REPLY` message | Forward it the same way to the successor: one `t3_thread_send` of the same text, no other action. The receiver's check doesn't depend on which thread delivered it, and a reply forwarded after the sender rotates still reaches the user. The only message in this thread is the `Moved to` reply. |
| Any other agent message | No action. Reply `Moved to <successor link>.` |
| A child's run started | Nothing. |
| The user wrote | Reply `Moved to <successor link>. This thread is retired; talk to the Chief of Staff there.` Take no action, even on an approval. They send it again in the current thread. |
| Its rate-limit wake fired | Nothing but the `Moved to` reply. Take over normally deletes this wake first, and the successor's startup.md § Start-up clean-up deletes any stray wake or legacy heartbeat that is not its own. |

## Thread rotation: Failed handoff

Failed handoff acts only when `rotation.from` is this thread's ID. For any other thread with a non-null `rotation` older than 10 minutes, do nothing. If the SKILL.md intro, or the failed handoff check on a retired thread's wake (an old child's notice, or a message from the user), finds `rotation.from` is this thread's ID and `rotation.startedAt` is more than 10 minutes old, the new thread never took over. Post `Rotation never confirmed. Rotation cancelled: <new thread link>.` to the user as your own reply (if `rotation.to` is null there is no link to give: post `Rotation never confirmed. Rotation cancelled.`), which also makes that message, not `Moved to`, your newest assistant message, so a Moved-to check on this thread no longer passes. `top` op: `rotation` to `null`, `chiefThreadId` to this thread, and `rotationHeldUntil` to 6 hours from now so SKILL.md § Full pass step 8 doesn't rotate again; `unretire` this thread; rename it back to `Chief of Staff` and pin it (`t3_thread_update`, `t3_thread_organize`), and keep running as the Chief of Staff (run the full SKILL.md § Full pass). That recovery ends with the `Rotation never confirmed` reply, not `Moved to`. A failed take over also posts `Rotation mismatch` in the new thread, which the user sees. A younger `rotation` means take over may still be running: do nothing, and a retired thread's turn still ends with `Moved to`.
