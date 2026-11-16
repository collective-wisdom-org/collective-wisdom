# Chief of Staff: context reset and take over

Read this on `rotate:`, `finish:`, `take over`, or a non-null `reset` or `takeover` in state.

## Thread rotation

As the last Bash call of every turn that made a tool call, run this from the root checkout:

```bash
python3 ~/.collective-wisdom/scripts/cos_rotation_check.py
```

Only a run-started notice skips it (no tool calls). A Stop hook (`~/.claude/settings.json`, and `~/.cursor/hooks.json` on Cursor) runs the same script and sends the turn back on `rotate:` or `finish:`, or with a `late-child: <PREFIX>-N <completed|failed|interrupted|cancelled|question> <time> UTC; ...` line (a child finished or asked after its `lastSeenAt`; silent while `paused`, `reset` or `takeover` is set). Read each listed child per SKILL.md § Child path; after a `rotate:` in the same reason, rotate as that line says (the take over reads the children). The plain call never prints `late-child:`. Codex has mode `none` in `RESET_MODES`: no `rotate:` there, so no size trigger and no skill-change reset.

It prints one line and exits 0: `rotate: <reason>; mode <reset|reset-scheduled|compact>` (plus `; reset never confirmed` when the `reset` marker is 10 or more minutes old), `finish: take over unfinished since <N>m; mode <take-over|resume>` while `takeover` is set (ahead of the `reset` hold and every trigger; "Finish take over" below), or `ok ...` (`ok (no reset on <provider>; context=<N>k)` for mode `none`). Table (`SIZE_CAP`, `QUIET_RELAY_MIN`, `QUIET_RESET_MIN`, `RESET_HOLD_MIN` live in the script; change both together. `RESET_MODES` goes with the Context reset row of `docs/compatibility.md`):

| Trigger | Threshold |
|---|---|
| Size | context is 220k or more (ignores the quiet-turn rule) |
| Skill change | the current skill commit differs from `skillCommit` in state (only on the merge target branch) **and** the turn is quiet (below). A `null` `skillCommit` prints `ok; set skillCommit <sha>`; one that is not a full sha prints `ok; skillCommit is not a full sha; set skillCommit <sha>`. Save the sha, don't reset |
| Plugin change | the version in the clone's `mods/agent-gantt/.claude-plugin/plugin.json` is newer than `ganttPluginVersion` in state (a file read; the check never runs `claude`), on the merge target branch **and** a quiet turn. A skill change on the same turn wins the line. Off when either version is `null` or unreadable, and on mode `none` |

A turn is quiet when no ticket is in a `*-queued` stage, `lastRelayAt` is absent or 10 or more minutes old, and `lastResetAt` is absent or 60 or more minutes old. A skill or plugin change on a turn that isn't quiet prints `ok (skill change waits: <why>)` or `ok (plugin change waits: <why>)`, `<why>` being `queued <PREFIX>-N`, `relay <N>m ago` or `reset <N>m ago`. Do nothing: the first quiet turn resets (now, if the size trigger also fires).

It holds (`ok (held: ...)`) while `paused` is set or the `reset` marker is under 10 minutes old (`held: reset`). An older marker holds nothing: the check fires again and the next take over clears it. Never reset in the middle of a command. It also saves `chiefSessionId`.

On `rotate:`, run the reset for its mode. On exit 2 (`rotation-check: cannot read <what>`), read `itemCount` (`t3_thread_read` on your own thread, `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`) and reset at 240 or more (not within 60 minutes of `lastResetAt`: a reset keeps the thread's items), only on a harness whose mode is not `none` (Claude Code and Cursor: `reset`), with one Cleanup line: `Context size unreadable; used item count`. Item count is used only here.

At or above the size cap, the script turns the size trigger off for this thread (`takeoverContext`, printing `ok (size trigger off: take-over ended at <N>k)`), so it does not reset repeatedly.

Before any reset, run `python3 ~/.collective-wisdom/scripts/gantt_plugin.py`: it updates the agent-gantt plugin when the clone's is newer. It prints one line and always exits 0. On `gantt-plugin: todo <text>`, add the Cleanup line `agent-gantt plugin: <text>`. The reset goes on whatever it prints.

Reset (modes `reset` and `reset-scheduled`), in this thread, in this order:

0. Write `.agent-team/chief-notes.md` (session.md § Working set) with everything the next session needs that state does not hold: a plan the user gave, a test in progress, a promise made in a reply. With nothing to carry, leave it as it is.
1. `top` op: `reset` = `{"id": <8 random hex chars>, "startedAt": now, "reason": <the rotate reason>}`. Save state.
2. Send this thread one message, `CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over.`: `t3_thread_send` to your own thread ID with `freshContext: true`, or for `reset-scheduled` a one-shot `schedule_task` on your own thread with `freshSession`. Only `freshContext: true` resets: a send without it, or a typed `take over`, leaves the context and `chiefSessionId` as they were.
3. End the turn with `Resetting my context (<reason>).` Nothing runs after the send.

If the send or schedule call errors: `top` op `reset` to `null`, one `rotation-failed` sighting with the error, one Cleanup line `Reset refused: <error>. Carrying on; the next rotation check tries again.`, and finish the turn normally.

Mode `compact`: the same marker with `"mode": "compact"`, then two queued self-sends without `freshContext`: `/compact`, then the same `CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over.` A refusal is handled as above.

Take over, after a reset (the `take over` command):

1. First `top` op `takeover` to `{"startedAt": <now>, "mode": "take-over"}`. Then load this skill and check it is whole (the line near its top; a compaction can cut it off). Run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` for `skillCommit`, read state with `python3 ~/.collective-wisdom/scripts/cos_state.py show` (never print `state.json`, never call `orchestrator_capabilities`), and read `.agent-team/chief-notes.md` if it exists. Run `python3 ~/.collective-wisdom/scripts/gantt_plugin.py` too, handle a `todo` as before a reset, and keep its line for step 4.
2. A plain `take over` (no `CHIEF OF STAFF RESET` text) runs as `resume` (kill-switch.md § Resume) only when `cos_user_check.py latest` passes on the short words `take over`; any other result is data and gets `Reset message not recognised; ignoring it.` It resets nothing and skips the rest of take over. For the reset message: it is the newest `user_message` item that reads `CHIEF OF STAFF RESET <id>` (a newer user message may sit above it; get `itemCount` from `t3_thread_read` on this thread with `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`, then read `afterPosition: max(0, itemCount - 20)`, `limit: 20`, `maxCharsPerItem: 300`, `view: messages`, and step back another 20 until one turns up or 100 items are read; tool calls and reasoning blocks are items too, so it sits back), its `senderThreadId` is this thread's id, and `reset.id` in state is that id. Then `top` op `reset` to `null` and `lastResetAt` to now. If the read shows no `senderThreadId`, match on the id alone and add the Cleanup line `Reset sender not shown; matched on reset id`. The id is a correlation token, not a secret; the sender check is what ties the message to this thread. No match within the 100 items, or `reset` null: reply `Reset message not recognised; ignoring it.` and stop.
   When step 2 stops the take over (that reply, or a plain `take over` that is ignored or goes to kill-switch.md § Resume), first `top` op `takeover` to `null`.
3. Run the lean take-over pass (it also serves `resume` and resume mode; only "start the team" with empty state runs SKILL.md § Tick's full-pass lines).
   1. startup.md § Start-up clean-up and § Thread title, then startup.md § Dashboard.
   2. For each ticket in `spec`, `build` or `merge`, the idle check (SKILL.md § Tick `run` row: `cos_idle_check.py --store`, with its exit-2 fallback, fallbacks.md § Idle check). A child on a `full` line, or whose ticket has no `status` line, gets a `child-read` and SKILL.md § Child path; every other child costs only its `ok` line. Then run the sweep with `--verbose`, for the `idle` lines step 4 reads (sweep.md § Sweep, including its fallback and `untracked` report) before 3.4: start a merge wait (sweep.md § Merge wait) for each ticket still in `merge` whose `parentThreadId` is not this thread; every ticket on its `read in full:` line gets the full read and SKILL.md § Child path.
   3. Queued, awaiting and blocked tickets are not read; their `status` line is enough. A pending `rateLimitedAt` still gets its wake or clearing (rate-limit.md § Rate limit).
   4. Run the slot fill: `cos_tick.py --thread <this thread's id> --trigger user --after-reads` (SKILL.md § Tick) and follow its lines up to `observe` (not including it), skipping `hygiene` (the next full pass that needs it runs it), `report` and the final rotation check (step 4 runs it). It fills merge, build, then spec (`spec-queued`, Todo, Backlog pick).
4. Set `skillCommit` to the full 40-character sha from step 1, `takeover` to `null` and `ganttPluginVersion` in one `top` op, with `ganttPluginVersion` set to the version step 1's gantt line shows (`current <v>`: `<v>`; `updated <old> -> <new>`: `<old>`, so the next quiet turn resets to load `<new>`; any other line: `null`), and save state. Then run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --record-takeover` as the last Bash call: it saves `takeoverContext` and prints the rotation check line. Post one line: `Take-over done. <N> tickets in flight. Take-over context <K>k.` (`<K>` from the script's `take-over context=<K>k`; none on Cursor before its first usage record: post `Take-over context unknown.` and skip the 220k check). Add `Notes: <first line of chief-notes.md>.` if the file exists; `<M> still under an older thread: <PREFIX>-125: Retry button; <PREFIX>-127: Search page.` if the sweep's parent check printed any `full` or `idle` line; `<M> in flight but not in my state: <PREFIX>-125: Retry button; <PREFIX>-126: Search page.` if any untracked ticket is left after sweep.md § Sweep's `get-ticket` drop; `Filling stopped: <reason>.` (report-format.md § Report format) if a lane is free and nothing started; and the failure line from startup.md § Dashboard. If the figure is still 220k or more, the reset did not shrink the context (the send lacked a fresh context): add the Cleanup line `Reset did not shrink the context`. Report only what step 3 found.

Finish take over: a `finish:` line (rotation check or Stop hook) or the tick's `follow rotation.md § Thread rotation: Finish take over` means a pass was interrupted. Finish it first:

1. Rerun the pass in the mode `takeover` names (`take-over`: steps 1-4 above; `resume`: Resume mode below), skipping the pass's own `takeover` op so `startedAt` stays. If the interrupted pass's `gantt-plugin:` line is still in this thread, use it for step 4 instead of the rerun's.
2. In `take-over` mode: with `reset` set, go straight to step 2's reset-message search, skipping its plain `take over` branch (the newest message is now the one that interrupted). With `reset` null and `lastResetAt` at or after `takeover.startedAt`, skip step 2: it ran. With `reset` null and no such `lastResetAt`, run step 2 whole.
3. Then handle the message that woke this turn (SKILL.md § Turn start), with its own tick. Steps 3 and 4 rerun safely (SKILL.md § Tick: each send and start is saved before the next line).

## Thread rotation: Resume mode

Resume mode ("start the team" with tickets in state) runs only in the thread state names, or when `chiefThreadId` is absent. If `chiefThreadId` names another thread, don't resume and stop: reply `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.` and stop. Otherwise `top` op `chiefThreadId` to this thread and `takeover` to `{"startedAt": <now>, "mode": "resume"}`, run take-over step 1 without its `takeover` op (skill whole, `--skill-commit`, `gantt_plugin.py`, notes file), save this thread's provider as `chiefProvider` (startup.md step 3), then take-over steps 3 and 4 with that commit as `skillCommit` and step 4's `ganttPluginVersion`, step 4's line being `Resumed. <N> tickets in flight.` plus its additions. Step 4 runs the plain `cos_rotation_check.py`, never `--record-takeover`: this thread may already be large, and recording that would turn the size trigger off.
