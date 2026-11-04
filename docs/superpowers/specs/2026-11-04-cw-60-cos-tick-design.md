# CW-60: A cos_tick.py that prints the tool calls a Chief of Staff turn needs

**Ticket:** [CW-60](https://github.com/dbeallor/collective-wisdom/issues/60)
**Status:** Draft

## Goal

The Chief of Staff (Sonnet) stops working out from prose which children to read, which sweep parts to run, which queued relay to send and which lane has room. One script reads state and the turn's trigger and prints the tool calls to make, in order. The model runs them and keeps judging only what needs judging: what a child's last message means, the approval brief, the readiness check.

## Today

Facts from `main` at `57e7470`, checked 2026-11-04.

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` is 555 lines, 65 KB. § Full pass (8 steps), § Slot fill (gate plus loop) and § Lean turns (reads, writes, notice turns, idle check, reports) say in which order and under which conditions to run `cos_state.py`, `cos_sweep.py`, `cos_idle_check.py`, `t3_thread_read`, `t3_pending_request`, `t3_thread_send`, `t3_thread_configure`, `delegate_task` and the tracker.
- 14 `cos_*.py` scripts each decide one thing. None decides the order of a turn. `cos_sweep.py` is the only one that runs others.
- The lane limits (spec 2, build 2, merge 1, overall 5) exist only as prose in § Lanes. No script knows them. `cos_state.py show` prints the counts and the queues sorted by `queuedAt`.
- The intro's retired-thread and failed-handoff checks, § Full pass step 4 (rate-limit wake and clearing), step 5 (hygiene child when `pm.lastDailyAt` is over 24 hours old), and § Rotation check (archive, then `cos_rotation_check.py` last) all decide from state alone.
- Decisions that need a tool result first: a child's marker (`SPEC READY` and so on) needs its thread read; the stuck check needs the run status and the wait check; the sweep and idle check name more children to read; the Todo start needs `list-tickets` and the readiness check.
- 21 pointers in other files name § Full pass, § Slot fill or § Lean turns (`rotation.md` 4, `startup.md` 4, `ticket-helper.md` 3, `state-keys.md` 2, `status.md` 1, `project-manager/SKILL.md` 2, `project-manager/reference.md` 4, one old spec). `test_section_pointers.py` fails on a pointer to a heading that is gone.

## Design

### Two calls per turn

A turn's plan depends on what the child reads find, and the script cannot read T3. So a turn calls the script twice:

1. `python3 scripts/cos_tick.py --thread <own id> --trigger <trigger>` prints the **look** plan: the state checks, the child reads, the idle check and the sweep. Its last line is `tick --after-reads`.
2. After the model has written what the reads found (the stage ops of the child path), `python3 scripts/cos_tick.py --thread <own id> --trigger <trigger> --after-reads` prints the **act** plan: rate limit, hygiene, slot fill, archive, rotation check, report.

The act plan is computed from state only, so it can be run again at any time. Rule in the skill: when a line fails or doesn't go as planned (a head check that moved, a user check that rejects, a readiness check that fails, a continuation that starts a new child), write what happened to state and run `--after-reads` again, then follow the new plan from its first line. Each send and start is saved to state before the next line, so a rerun never sends or starts the same ticket twice.

### Triggers

| Trigger | When the model runs it |
|---|---|
| `start` | `start the team`. Empty state: the setup steps of `startup.md` § Setup, start-up clean-up, then the full pass. Tickets in state: one line, `follow rotation.md § Thread rotation: Resume mode`, and nothing else. |
| `user` | Any user message that runs a full pass, after the command itself is applied per § Commands. |
| `wake` | `run /chief-of-staff wake`. With `wakeTaskId`: delete the wake, clear `wakeTaskId`, then the full pass. Without: start-up clean-up step 1 only. |
| `notice:<thread>` | A run-finished notice or a forwarded `CHIEF OF STAFF NOTICE:` for that thread. |
| `status` | `status` or `where's <PREFIX>-N?`. |

Not run at all: run-started notices and run-finished notices for the project manager children (they make no tool calls), ticket helper and cross-repo turns that run no full pass, `take over` and `resume`.

### Plan lines

Numbered lines, one tool call or one named step each. Arguments come from state. Text from state that a line passes on (a `pendingRelay`) is printed as a JSON string so newlines survive.

| Line | Meaning |
|---|---|
| `stop <reason>` | End the turn here. Reasons: `retired` (rotation.md § Thread rotation: Retired thread), `failed-handoff` (rotation.md § Thread rotation: Failed handoff), `paused` (answer commands only). |
| `read <PREFIX>-N <child> afterPosition=<p> limit=5 runLimit=1 maxCharsPerItem=2000` | `t3_thread_read`, then § Child path for that ticket. |
| `pending <child>` | `t3_pending_request` action `list`. |
| `idle-read <PREFIX>-N <child>` | `t3_thread_read` with `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`. |
| `run <command>` | A Bash call, written out in full with `AGENT_GH_ROLE=chief-of-staff` where the script calls `gh.sh`, and `<<'EOF'` where it takes stdin (the idle check gets the `idle-read` results). |
| `each full: read` | For each `full` line of the idle check and each ticket on the sweep's `read in full:` line not already read this turn: a `read` line, then § Child path. |
| `helper-test <thread>` | ticket-helper.md § Helper test (notice for a thread not in `tickets`). |
| `delete-wake <id>`, `schedule-wake everyMs=<ms>`, `clear-rate-limit` | § Rate limit. `schedule-wake` is printed when `rateLimitedAt` is set, `wakeTaskId` is null and `wakeAt` is in the future; `clear-rate-limit` when `wakeAt` is past. |
| `hygiene` | project-manager/reference.md § Hygiene child. Printed on `start`, and on `user` and `wake` when `pm.lastDailyAt` is null, malformed or over 24 hours old, never while `paused` or `rateLimitedAt` is set. |
| `prune` | `cos_state.py apply` with `prune`. |
| `head-check <PREFIX>-N pr=<N> head=<sha>` | § Send or queue head check, before a queued merge approval goes out. |
| `user-check <PREFIX>-N <thread> <itemId>` | The queued spec approval re-read (`cos_user_check.py item`), with the quoted words from `pendingRelay`. |
| `configure <child> claude-sonnet-5-5 effort=high` | The § Models switch, before a spec approval. |
| `continuation <PREFIX>-N <lane>` | continuation.md § Continuation child, in place of `send`, when `parentThreadId` is set and is not `chiefThreadId`. |
| `send <PREFIX>-N <lane> <relay as JSON>` | `t3_thread_send`, then a `stage` op to the lane's active stage that clears `pendingRelay`, `approvalItemId` and `queuedAt`. |
| `rebuild-relay <PREFIX>-N` | A queued ticket with no `pendingRelay`: rebuild it or send it back to `awaiting-*`, as § Send or queue says. |
| `start-todo` | One Todo start: `list-tickets` once per turn, then § Readiness check and start on the next startable ticket, then `project-manager` § Backlog pick when Todo has none. Printed once per free spec slot. |
| `archive <thread>` | rotation.md § Thread rotation "Archiving", for a `retiredThreads` entry without `archivedAt`. |
| `run python3 scripts/cos_rotation_check.py` | Always the last tool call. |
| `report` | § Report format, only if the turn changed what the user sees. The script also prints the slot-fill stop reason (`lanes full`, `nothing queued`, or `spec slot free`) so the `Filling stopped:` line names it. |

### What each trigger plans

Look plan:

- Every trigger: the retired and failed-handoff checks from state (the SKILL.md intro rules), with `--thread`. `paused` stops after them, except `status`.
- `start`, `user`, `wake` (full pass): `read` and `pending` for every ticket in `spec`, `build` or `merge`; then the sweep; then `each full: read`.
- `notice:<thread>` for an active ticket's child: `read` and `pending` for it; `idle-read` for every other active child; the idle check with `--skip <that ticket>`; the sweep; `each full: read`.
- `notice:<thread>` for a ticket not in an active stage (cancelled, queued, awaiting, blocked): its own steps are skipped; idle reads, idle check, sweep as above.
- `notice:<thread>` for a thread not in `tickets`: `helper-test`, then as above.
- `status`: idle reads for every active child, the idle check, the sweep, `each full: read`. Its act plan is only the rotation check, unless a read changed a stage; then the model runs `--after-reads` for the slot fill.

Act plan:

- Full pass: rate-limit lines, `hygiene`, `prune`, slot fill, `archive`, rotation check, `report`.
- Notice: slot fill, `archive`, rotation check, `report`.
- Slot fill, from state: skipped when `paused` or `rateLimitedAt` is set. Otherwise loop while the overall count is under the cap: take the first lane, in the order merge, build, spec, that has a free slot and a queued ticket (oldest `queuedAt`), and print its pre-steps and `send` (or `continuation`); count it as moved. Then one `start-todo` per remaining free spec slot. The look plan already read or idle-checked every active child, so the gate's lane-full idle check is never needed again inside a tick.

### Where the lane limits live

`cos_tick.py` holds the limits as constants (`spec 2, build 2, merge 1, overall 5`). § Lanes keeps its table, which says the script holds the numbers and a change goes through both.

### Skill changes

In `agent-team/.claude/skills/chief-of-staff/SKILL.md`:

- § Full pass and § Slot fill are replaced by one § Tick section: the two calls, the rerun rule, and the plan-line table above. That section is the only order the turn follows.
- New § Child path holds the judgement that stays with the model, taken from § Full pass steps 2 to 4: reading the markers and the stage op for each, the `nextPosition` write, the pending request, the stuck check with the wait check and the restart message, and how a rate-limit error sets `rateLimitedAt` and its reset time.
- § Rate limit holds the judgement part of step 4: reset time from T3's run error only, the 3-minute to 6-hour bounds, and resuming tickets blocked by a rate limit with `rateLimitResumes` below 3.
- § Lean turns keeps Reads, Writes and Reports. Its Notice turns and Idle check bullets go: the script plans those now.
- The intro's per-trigger bullets shrink to "run the tick with this trigger".
- Every pointer to § Full pass, § Slot fill or § Lean turns "Notice turns" in the other files moves to § Tick, § Child path or § Rate limit, so `test_section_pointers.py` passes.
- The readiness check, the approval brief, § Send or queue, § Commands, § Report format and the reference files stay prose.

### Tests

`agent-team/scripts/test_cos_tick.py`, table-driven over fixture states:

- A notice turn: the read, pending, idle reads, idle check, sweep and `tick --after-reads` lines, for an active child, a cancelled ticket and an unknown thread.
- A user turn: one read per active child, the sweep, and the hygiene line when due and not when fresh.
- A start-up turn: setup lines with empty state; the resume-mode line with tickets.
- The act plan: merge before build before spec, oldest `queuedAt` first, limits and cap respected across several sends, the pre-steps for a spec approval and a merge approval, `continuation` for a ticket under an older thread, nothing when `paused` or rate limited, `start-todo` count.
- Retired, failed-handoff and paused stops.

## Calls I made

- Two calls per turn, not one. The plan after the child reads depends on what they found, and the script cannot read T3. The ticket's single call would have to print every branch as conditions, which puts the interpreting back on the model.
- The script prints named steps (`start-todo`, `each full: read`, `continuation`) where the next tool calls depend on tracker or thread results. It doesn't take those results on stdin to plan further; rerunning `--after-reads` covers that.
- `take over`, `resume` and resume mode stay as rotation.md prose. The ticket's trigger list leaves them out, and they run once per rotation.
- The lane limits move into the script as constants. Today no code knows them, and a plan needs them.
- The pending request check (`t3_pending_request`) is planned for each child read, as step 2 says today.
- `status` runs no slot fill unless a read moved a stage, as today; the model then runs `--after-reads`.
- The gate's lane-full idle check is dropped inside a tick, since every trigger that fills already read or idle-checked every active child. It changes nothing a turn does today.
- § Lean turns Reads, Writes and Reports stay. They are how to make a call, not which calls to make.
- `cos_tick.py` writes nothing. State writes stay with `cos_state.py apply`, run by the model.

## Leaves out

- Moving T3 calls out of the model (ticket's out of scope).
- The approval brief, readiness check, report wording and § Commands.
- Shrinking the other reference files (#23).

## Touches

None of data, money, auth, user email or migrations. It changes how the Chief of Staff orders its turns.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` passes, including `test_cos_tick.py` and `test_section_pointers.py`.
- `grep -n "## Full pass\|## Slot fill" agent-team/.claude/skills/chief-of-staff/SKILL.md` finds nothing.
- Run `cos_tick.py` against a copy of a real state file for each trigger and compare with what the old § Full pass and § Slot fill say.
