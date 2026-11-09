# Chief of Staff: handoff and rotation

Read this on `rotate:`, `take over`, a retired thread, or a non-null `rotation` in state.

## Thread rotation

As the last Bash call of every turn that made a tool call, run this from the root checkout:

```bash
python3 ~/.collective-wisdom/scripts/cos_rotation_check.py
```

Only a run-started notice skips it (no tool calls). A retired thread never runs it, since it would claim `chiefSessionId`. A Stop hook (`~/.claude/settings.json`, and `~/.cursor/hooks.json` on Cursor) runs the same script and sends the turn back on `rotate:`. Cursor reports no context size, so only a skill change rotates there.

It prints one line, `ok ...` or `rotate: <reason>`, and exits 0. Table (`SIZE_CAP`, `QUIET_RELAY_MIN`, `QUIET_ROTATED_MIN` live in the script; change both together):

| Trigger | Threshold |
|---|---|
| Size | context is 220k or more (ignores the quiet-turn rule) |
| Skill change | the current skill commit differs from `skillCommit` in state (only on the merge target branch) **and** the turn is quiet (below). A `null` `skillCommit` prints `ok; set skillCommit <sha>`, save it and don't rotate |

A turn is quiet when no ticket is in a `*-queued` stage, `lastRelayAt` is absent or 10 or more minutes old, and the newest `retiredAt` in `retiredThreads` is 60 or more minutes old (or there is none). A skill change on a turn that isn't quiet prints `ok (skill change waits: queued <PREFIX>-N | relay <N>m ago | rotated <N>m ago)`. Do nothing: the first quiet turn rotates (now, if the size trigger also fires).

It holds (`ok (held: ...)`) while `paused` or `rotation` is set or `rotationHeldUntil` is in the future. Never rotate in the middle of a command. It also saves `chiefSessionId`.

On `rotate:`, run the handoff below. On exit 2 (`rotation-check: cannot read <what>`), read `itemCount` (`t3_thread_read` on your own thread, `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`) and rotate at 240 or more, with one Cleanup line: `Context size unreadable; used item count`. Item count is used only here.

A take-over turn that ends above 90k adds a Cleanup line, `Take-over ended at <N>k; working set is larger than it should be`. At or above the size cap, the script turns the size trigger off for this thread (`takeoverContext`, printing `ok (size trigger off: take-over ended at <N>k)`), so it does not rotate repeatedly.

**Archiving.** At the end of a turn that ran the tick or the take-over pass, before the rotation check, archive only a prefix of `retiredThreads` (oldest first, entries without `archivedAt`): an entry qualifies only if no ticket has it or any older entry as `parentThreadId` and every ticket's `parentThreadId` is known; stop at the first that fails. `python3 ~/.collective-wisdom/scripts/cos_parent_check.py --thread <this thread's id>` applies that rule: archive only the threads on its `archive` lines, in order, with `t3_thread_organize` `archive`, set `archivedAt` to now, then at once `t3_thread_read` it (`limit: 1`, `maxCharsPerItem: 1`). If that read fails, `unarchive` it, clear `archivedAt`, archive nothing more, and report once under Cleanup.

**Moved-to check** on a thread X (the successor fallback, take over, the rebuild and the children's chain check): `t3_thread_read` X with `limit: 1`, `maxCharsPerItem: 1` for `itemCount`, then from `afterPosition: max(0, itemCount - 8)` with `limit: 8`, `maxCharsPerItem: 300`, `view: messages`. Count only items with `type: "assistant_message"`, `creationSource: "provider"`, `visibility: "local"` and `sourceThreadId` equal to X's id; if none of the 8 counts, step back another 8 until one does or you reach the thread start. It passes when the newest counted item starts with `Moved to`. The successor's id is the URI inside the markdown link's parentheses (or the bare `<t3-thread://...>` link in a message posted before CW-134). A `t3_thread_send` or copied-in message does not count.

A retired thread's newest assistant message always passes, and each retired thread points to its own successor (A to B, B to C). Nobody else writes a `Moved to` message.

Handoff, in the old thread:

1. Set `rotation` to `{from: <own id>, to: null, startedAt: now}`. Save state.
2. `t3_thread_launch` with `title: "Chief of Staff"`, `workspaceStrategy: {type: "root"}`, `modelSelection: {instanceId: "claudeAgent", model: "claude-sonnet-5-5", options: {effort: "medium"}}` (SKILL.md § Models; on Cursor, § Models Cursor), and this message:

   ```
   CHIEF OF STAFF ROTATION from <old thread id>.
   Run /chief-of-staff take over.
   ```

3. Set `rotation.to` to the new thread ID. Save state.
4. `t3_thread_update` rename to `Chief of Staff (old)`, `t3_thread_organize` unpin.
5. In one `apply`, set `chiefThreadId` to the new thread ID and `chiefSessionId` to `null` (`top` op; quiets this thread's Stop hook), and `retire` the old thread's ID with `successor` set to the new thread ID. Save state. This is the last tool call.
6. End the turn with `Moved to [<title>](<new thread link>). Talk to me there.` as your own reply text. Never `t3_thread_send` it: that makes a `user_message` with `creationSource: "mcp"`, which the Moved-to check never counts.

A turn that dies between steps 5 and 6 is a failed handoff (below).

Take over, in the new thread (the `take over` command):

1. Load this skill, run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` for `skillCommit`, and read state with `python3 ~/.collective-wisdom/scripts/cos_state.py show` (never print `state.json`, never call `orchestrator_capabilities`). Confirm the `take over` message is this thread's first item (`afterPosition: 0`, `limit: 1`), the Moved-to check on this thread fails, `rotation.to` is this thread and `rotation.from` matches the launch message's id. Then the Moved-to check on `rotation.from` must pass, its link naming this thread. If `rotation.from` matches but `rotation.to` is null, or the check does not pass yet, the old thread has not finished: `sleep 10`, re-read state and re-check, up to 5 times, before calling it a mismatch. Then stop, posting `Rotation mismatch: <one line>` for a state mismatch, or `Rotation mismatch: no Moved to message in [<title>](<old link>)` if the check never passes. Schedule nothing.
2. If state has `wakeTaskId`, delete it as startup.md § Deleting the wake says (it is bound to the old thread) and clear `wakeTaskId` (keep `wakeAt`). Step 4 makes a new one if a rate limit still needs it.
3. `t3_thread_organize` pin this thread. Set `rotation` to `null`. In `take over` only, not resume mode, post `Taking over from [<title>](<old thread link>). Checking the tickets in flight; a summary follows.` as your own reply text (never `t3_thread_send`) and go on to step 4 in the same turn. Every `Rotation mismatch` stop comes before this line.
4. Run the lean take-over pass (it also serves `resume` and resume mode; only "start the team" with empty state runs SKILL.md § Tick's full-pass lines).
   1. startup.md § Start-up clean-up, then the dashboard step (startup.md Setup step 4).
   2. For each ticket in `spec`, `build` or `merge`, the idle-check read (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`). A child that is running and idle over 45 minutes, whose `updatedAt` is later than its `lastSeenAt`, or whose ticket has no `status` line, gets the full read and SKILL.md § Child path; every other child costs only that small read. Then run the sweep (SKILL.md § Sweep, including its fallback and `untracked` report) before 4.4: start a merge wait (SKILL.md § Merge wait) for each ticket still in `merge` whose `parentThreadId` is not this thread; every ticket on its `read in full:` line gets the full read and SKILL.md § Child path.
   3. Queued, awaiting and blocked tickets are not read; their `status` line is enough. A pending `rateLimitedAt` still gets its wake or clearing (SKILL.md § Rate limit).
   4. Run the slot fill: `cos_tick.py --thread <this thread's id> --trigger user --after-reads` (SKILL.md § Tick) and follow its lines up to `observe` (not including it), skipping `hygiene` (the next full pass that needs it runs it), `report` and the final rotation check (step 5 runs it). It fills merge, build, then spec (`spec-queued`, Todo, Backlog pick).
5. Set `skillCommit` to the commit from step 1 and save state. Then run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --record-takeover` as the last Bash call: it saves `takeoverContext` and prints the rotation check line. Post one line: `Take-over done. <N> tickets in flight. Take-over context <K>k.` (`<K>` from the script's `take-over context=<K>k`). Add `<M> still under an older thread: <PREFIX>-125, <PREFIX>-127.` if the sweep's parent check printed any `full` or `idle` line; `<M> in flight but not in my state: <PREFIX>-125, <PREFIX>-126.` if any untracked ticket is left after SKILL.md § Sweep's `get-ticket` drop; `Filling stopped: <reason>.` (SKILL.md § Report format) if a lane is free and nothing started; and the dashboard step's failure line. Report only what step 4 found.

If the user writes in the `rotation.to` thread while `rotation` is non-null, take over never ran. Within 10 minutes of `rotation.startedAt`, run take over before their command. After that the old thread's failed handoff may be recovering: don't take over, reply `Rotation never confirmed; write in [<title>](<old thread link>).` Re-run step 1's check on the old thread just before step 3; stop with `Rotation mismatch` if `rotation` changed or the check fails.

## Thread rotation: Resume mode

Resume mode ("start the team" with tickets in state) runs only in the thread state names, or when `chiefThreadId` is absent. If `chiefThreadId` names another thread, don't resume and stop: if this thread is in `retiredThreads`, reply `Moved to [<title>](<its successor link>). This thread is retired; talk to the Chief of Staff there.` (successor as § Thread rotation: Retired thread gives it; with none, take no action and give its no-successor reply), else reply `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.` and stop. Otherwise `top` op `chiefThreadId` to this thread and `unretire` it, run `cos_rotation_check.py --skill-commit` (take-over step 1 would have), then take-over steps 2 to 5 with that commit as `skillCommit`, step 5's line being `Resumed. <N> tickets in flight.` plus its additions. Step 5 runs the plain `cos_rotation_check.py`, never `--record-takeover`: this thread may already be large, and recording that would turn the size trigger off.

## Thread rotation: Retired thread

The tick prints `stop retired` when `chiefThreadId` is not this thread's ID, or this thread's ID is in `retiredThreads` (a younger `rotation` included: the new thread may still be taking over); a turn with no tick (take over, `resume`, ticket helper, cross-repo) applies it by hand. A retired thread does only what this section says. A run-started notice, and a run-finished notice for a project manager child, skip it. `take over` and `start the team` skip it and § Thread rotation: Failed handoff only as the new thread of an unfinished handoff: `rotation.to` is this thread, or `rotation.to` is null and `rotation.from` matches the id in the launch message (take over) or state names this thread as `chiefThreadId` or has none (start the team). Otherwise both checks apply, and a message that fails them gets no reply naming a successor.

Its successor is the `successor` of its `retiredThreads` entry; for an entry without one, or no entry, the link in the newest assistant message the Moved-to check finds on this thread, once per wake, for the link only. If that fails too, name no successor, take no action, and if the user wrote, reply `State says this thread is retired but names no successor. Check .agent-team/state.json.`

On any wake except a run-started notice, first run § Thread rotation: Failed handoff if `rotation` is non-null. Every other retired-thread turn (failed-handoff recovery aside) ends with the reply `Moved to [<title>](<successor link>).` A retired thread is woken by:

| What woke it | It does |
|---|---|
| A child's run finished | `t3_thread_send` to the successor: `CHIEF OF STAFF NOTICE: child <child thread id> finished a run.` No other calls. |
| A `CHIEF OF STAFF NOTICE:` message | Forward it the same way: one `t3_thread_send` of the same text to the successor, no other action. |
| A `CHIEF OF STAFF REQUEST` or `CHIEF OF STAFF REPLY` message | Forward it the same way. |
| Any other agent message | No action. Reply `Moved to [<title>](<successor link>).` |
| A child's run started | Nothing. |
| The user wrote | Reply `Moved to [<title>](<successor link>). This thread is retired; talk to the Chief of Staff there.` Take no action, even on an approval; they send it again in the current thread. |
| Its merge wait ended | Nothing but the `Moved to` reply (its successor started its own wait at take over). |
| Its rate-limit wake fired | Nothing but the `Moved to` reply (take over normally deletes this wake first; startup.md § Start-up clean-up deletes any stray one). |

For the first three rows, the only message in this thread is the `Moved to` reply.

## Thread rotation: Failed handoff

The tick prints `stop failed-handoff` when `rotation` is non-null, `rotation.from` is this thread's ID and `rotation.startedAt` is more than 10 minutes old. A retired thread's wake and a turn with no tick apply the same rule, retired or not (a handoff that died before step 5 leaves it not retired). Any other thread, and any `rotation` younger than that (take over may still be running), does nothing; a retired thread's turn still ends with `Moved to`.

The new thread never took over. Post `Rotation never confirmed. Rotation cancelled: [<title>](<new thread link>).` to the user as your own reply (if `rotation.to` is null there is no link: `Rotation never confirmed. Rotation cancelled.`). That message, not `Moved to`, is now your newest assistant message, so a Moved-to check on this thread fails. `top` op: `rotation` to `null`, `chiefThreadId` to this thread, and `rotationHeldUntil` to 6 hours from now so the rotation check doesn't rotate again; `unretire` this thread; rename it back to `Chief of Staff` and pin it (`t3_thread_update`, `t3_thread_organize`), and keep running as the Chief of Staff (SKILL.md § Tick, with the trigger of the message that woke this thread). 
