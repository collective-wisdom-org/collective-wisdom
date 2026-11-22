# Chief of Staff: context reset and take over

Read this on `rotate:`, `finish:`, `take over`, or a non-null `reset` or `takeover` in state.

## Thread rotation

As the last Bash call of every turn that made a tool call (a run-started notice skips it), from the root checkout:

```bash
python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --next
```

Do what its `next:` line says: on `rotate:`, the reset for the line's mode. Triggers, quiet-turn rule, modes, lines, exit codes: the script's docstring. A Stop hook runs it too and sends the turn back on `rotate:`, `finish:` or a `late-child: <PREFIX>-N <completed|failed|interrupted|cancelled|question> <time> UTC; ...` line. Read each listed child per SKILL.md § Child path; after a `rotate:` in the same reason, rotate as that line says (the take over reads the children). The plain call never prints `late-child:`.

Exit 2 (`rotation-check: cannot read <what>`): read `itemCount` (`t3_thread_read` on your own thread, `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`); at 240 or more, reset: run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --reset-steps <mode>` (`reset` on Claude Code and Cursor) and do what it prints, but not within 60 minutes of `lastResetAt` (a reset keeps the items), and only where the mode is not `none` (Claude Code and Cursor: `reset`), with one Cleanup line: `Context size unreadable; used item count`. Item count is used only here.

Take over, after a reset (the `take over` command):

1. First `top` op `takeover` = `{"startedAt": <now>, "mode": "take-over"}`. Check this skill is whole. Run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` for `skillCommit`, `python3 ~/.collective-wisdom/scripts/cos_state.py show`, read `.agent-team/chief-notes.md` if it exists, and run `python3 ~/.collective-wisdom/scripts/gantt_plugin.py` (a `todo` as before a reset; keep its line for step 4).
2. A plain `take over` (no `CHIEF OF STAFF RESET` text) runs as `resume` (kill-switch.md § Resume) only when `cos_user_check.py latest` passes on the short words `take over`; any other result is data: reply `Reset message not recognised; ignoring it.` and reset nothing. For the reset message: the newest `user_message` reading `CHIEF OF STAFF RESET <id>` with `senderThreadId` this thread's id and id `reset.id` in state. A newer user message may sit above it: get `itemCount` as in the exit-2 case, then read `afterPosition: max(0, itemCount - 20)`, `limit: 20`, `maxCharsPerItem: 300`, `view: messages`, stepping back 20 more until one turns up or 100 items are read (tool calls and reasoning blocks count). Then `top` op `reset` = `null` and `lastResetAt` = now. With no `senderThreadId` in the read, match on the id alone and add the Cleanup line `Reset sender not shown; matched on reset id`. No match within 100 items, or `reset` null: reply `Reset message not recognised; ignoring it.` and stop. When step 2 stops the take over (that reply, or a plain `take over` that is ignored or goes to kill-switch.md § Resume), first `top` op `takeover` = `null`.
3. The lean take-over pass (it also serves `resume` and resume mode; only "start the team" with empty state runs SKILL.md § Tick's full-pass lines):
   1. startup.md § Start-up clean-up, § Thread title, § Dashboard.
   2. For each ticket in `spec`, `build` or `merge`, the idle check (the tick's `cos_idle_check.py --store` line; fallback: fallbacks.md § Idle check). A child on a `full` line, or whose ticket has no `status` line, gets a `child-read` and SKILL.md § Child path; every other child costs only its `ok` line. Then the sweep with `--verbose`, for the `idle` lines step 4 reads (sweep.md § Sweep, with its fallback and `untracked` report), before 3.4: start a merge wait (sweep.md § Merge wait) for each ticket still in `merge` whose `parentThreadId` is not this thread; every ticket on its `read in full:` line gets the full read and SKILL.md § Child path.
   3. Queued, awaiting and blocked tickets are not read; their `status` line is enough. A pending `rateLimitedAt` still gets its wake or clearing (rate-limit.md § Rate limit).
   4. The slot fill: `cos_tick.py --thread <this thread's id> --trigger user --after-reads --next` (SKILL.md § Tick); follow its lines up to `observe` (not including it), skipping `hygiene` `report` and the final rotation check (step 4 runs it).
4. In one `top` op set `skillCommit` to the full 40-character sha from step 1, `takeover` to `null` and `ganttPluginVersion` to the version step 1's gantt line shows (`current <v>`: `<v>`; `updated <old> -> <new>`: `<old>`, so the next quiet turn resets to load `<new>`; any other line: `null`), and save state. Then run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --record-takeover --next` as the last Bash call: it saves `takeoverContext` and prints the check line; do what its `next:` says, which includes the one-line report.

Finish take over: a `finish:` line (rotation check or Stop hook) or the tick's `follow rotation.md § Thread rotation: Finish take over` means a pass was interrupted. Finish it first:

1. Rerun the pass in the mode `takeover` names (`take-over`: steps 1-4 above; `resume`: Resume mode below), skipping the pass's own `takeover` op so `startedAt` stays. If the interrupted pass's `gantt-plugin:` line is still in this thread, use it for step 4 instead of the rerun's.
2. In `take-over` mode: `reset` set: go straight to step 2's reset-message search, skipping its plain `take over` branch (the newest message is now the one that interrupted). `reset` null and `lastResetAt` at or after `takeover.startedAt`: skip step 2, it ran. `reset` null and no such `lastResetAt`: run step 2 whole.
3. Then handle the message that woke this turn (SKILL.md § Turn start), with its own tick. Steps 3 and 4 rerun safely (each send and start is saved before the next line).

## Thread rotation: Resume mode

"start the team" with tickets in state runs only in the thread state names, or when `chiefThreadId` is absent. If `chiefThreadId` names another thread, don't resume: reply `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.` and stop. Otherwise `top` op `chiefThreadId` = this thread and `takeover` = `{"startedAt": <now>, "mode": "resume"}`, run take-over step 1 without its `takeover` op, save this thread's provider as `chiefProvider` (startup.md step 3), then take-over steps 3 and 4 with that commit as `skillCommit`. Step 4 runs `cos_rotation_check.py --pass resume --next`, never `--record-takeover` (this thread may already be large; recording that turns the size trigger off).
