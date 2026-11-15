# WISE-435: Send the Chief of Staff back to read a child that finished while it was mid-turn

**Status:** Shipped
**Ticket:** [#435](https://github.com/collective-wisdom-org/collective-wisdom/issues/435)
**Shipped:** in PR #449, as specified

## Goal

When a child finishes while the Chief of Staff is in the middle of a turn, the Chief of Staff reads it before that turn ends, instead of waiting for the late notice and for the user to point it out.

## Today

Facts from main at `8c018e1`.

- T3 delivers a child's run-finished notice only when the Chief of Staff's thread is idle. A notice sent mid-turn waits, so the turn ends without the read (the WISE-428 sighting in the ticket).
- The Stop hook (`~/.claude/settings.json`, `cos_rotation_check.py --hook`, `run_hook`) runs only for `chiefSessionId`, skips a stop with `stop_hook_active` (Cursor: `loop_count` non-zero or `status` not `completed`), and blocks with `{"decision": "block", "reason": ...}` (Cursor: `{"followup_message": ...}`) on a `rotate:`, `finish:` or `cannot read` line. It does not look at children.
- `cos_idle_check.py` reads T3's store read-only (`store_rows`, `mode=ro`, default `~/.t3/userdata/statev2.sqlite`). Its `check()` flags `full <ticket> lost-notice` when a child's run is not running and the thread's `updated_at` is newer than `lastSeenAt`, and flags every other non-running child `not-running` every time. It runs only inside a tick.
- The store's `orchestration_v2_projection_runs` has `status` (`completed`, `failed`, `interrupted`, `cancelled`, `running`, and the waiting states `queued`, `preparing`, `starting`, `waiting`) and `completed_at`. `orchestration_v2_projection_runtime_requests` holds a thread's questions (`kind` `user_input`, `command`, `file-read`) with `status` `pending` or `resolved` and `created_at`.
- After each child read the Chief of Staff saves `lastSeenAt` now (SKILL.md § Tick, `child-read`). Entering `awaiting-*` or `blocked` stamps it too, but those stages are not active.

## Design

### The check (`cos_idle_check.py`)

A new function `late_children(state, db)` returns one entry per active ticket (stage `spec`, `build` or `merge`) that needs a read. It opens the store with the existing `store_rows` and, per ticket, reads the child thread (`childThreadId`) newest run (`ORDER BY ordinal DESC LIMIT 1`) and any pending runtime request.

A ticket is listed when either holds:

1. **Finished since last seen.** The newest run's status is `completed`, `failed`, `interrupted` or `cancelled`, and its `completed_at` is after `lastSeenAt` (a missing or unreadable `lastSeenAt` counts as never seen). Entry: `<ticket> <status> <h:mm am/pm> UTC`.
2. **Question since last seen.** A runtime request on the child thread has `status` `pending` and `created_at` after `lastSeenAt`. Entry: `<ticket> question <h:mm am/pm> UTC`.

A `completed` run that ended in a matched `t3_background_wait` (the existing `check_wait` on `wait_read_from_store`, exit 0) is not listed: the child is waiting on its own command, and the command's exit wakes it, not the Chief of Staff.

It compares the run's `completed_at`, not the thread's `updated_at`. A Chief of Staff send into a child moves the thread's `updated_at` and queues a new run, so `updated_at` would flag the turn that sent; the new run is the newest one and is not finished, so `completed_at` stays quiet. The tick's `check()` and its `lost-notice` and `not-running` lines do not change.

Any store error, a missing table or column, or a missing database returns nothing (no exception to the caller). A ticket with no `childThreadId` or whose thread is missing from the store is skipped: the tick's idle check already reports those as `unread`.

### The hook (`cos_rotation_check.py --hook`)

`run_hook` calls `late_children` after the rotation line, under the same gates: a repo with `docs/agents/project.md`, the machine copy of the script, the Chief of Staff's session, and not a second stop (`stop_hook_active`, or Cursor's `loop_count`). It also stays silent when `paused` is set, and while a `reset` or `takeover` marker is set (a reset ends the turn right after its send, and the take-over pass reads every active child anyway).

With entries, the hook sends the turn back with this line:

```
late-child: WISE-428 completed 6:12 pm UTC; WISE-430 question 6:20 pm UTC; read each per chief-of-staff SKILL.md § Child path
```

When the rotation line also fires, the reason is the rotation reason followed by `; ` and the `late-child:` line. Rotation keeps its instruction (rotation.md § Thread rotation); a take over then reads the children as part of its pass.

On Cursor the same text goes in `followup_message`. The T3 store is the same for a Cursor thread in T3, so nothing differs there.

The check does not repeat. The turn it sends back reads the child (`child-read`) and saves `lastSeenAt` after the run's `completed_at`, or moves the ticket out of the active stages, so the next stop is quiet. `stop_hook_active` keeps a single stop from being sent back twice.

Plain mode (the model's own `cos_rotation_check.py` call at the end of a turn) does not change: it prints one line, which the docs and the tick read.

### Docs

- `chief-of-staff/rotation.md` § Thread rotation: name the `late-child:` line beside `rotate:` and `finish:`, and say to read each listed child per SKILL.md § Child path, then end the turn as usual.
- `chief-of-staff/SKILL.md` § Turn start: one line that a `late-child:` Stop hook reason is handled like a run-finished notice for each ticket it names.
- `cos_rotation_check.py` and `cos_idle_check.py` docstrings name the new line and function.

### Test

One table-driven test in `test_cos_rotation_check.py`, with a state file and a fake store (the `make_store` shape from `test_cos_idle_check.py`, plus a `orchestration_v2_projection_runtime_requests` table):

| Case | Hook prints |
|---|---|
| `build` child, newest run `completed` after `lastSeenAt` | block reason naming the ticket and `completed` |
| `failed` run after `lastSeenAt` | block reason naming `failed` |
| pending question after `lastSeenAt` | block reason naming `question` |
| child running | nothing |
| `lastSeenAt` after the run's `completed_at` (already read) | nothing |
| completed run ending in a matched `t3_background_wait` | nothing |
| `paused` | nothing |
| `stop_hook_active` true | nothing |
| store unreadable (no file, or a table missing) | nothing |
| late child and rotation fires | rotation reason, then the `late-child:` line |

The "already read" row covers the acceptance line that the same finish does not send the next turn back.

## Leaves out

- How T3 delivers notices.
- A timer or scheduled wake (#16).
- The lost-notice safety net for notices that never arrive (#406, #386).
- Changes to the tick's idle check lines.

## Calls I made

- **A pending question counts.** The store does show it (`runtime_requests`, `status` `pending`), so it is covered rather than deferred.
- **The run's `completed_at`, not the thread's `updated_at`.** This avoids a false send-back on the turn where the Chief of Staff sent into a child. It means the hook and the tick's `lost-notice` line use different timestamps; the tick's line is left alone to keep this ticket in scope.
- **A child waiting on its own background command is skipped**, using the existing wait check, so a run that ended in `t3_background_wait` does not cost a read that finds nothing.
- **Silent while a `reset` or `takeover` marker is set**, so the check never adds work after a reset's send, and a take over reads the children itself.
- **Rotation and late children share one reason**, rotation first, rather than one hiding the other.
- **Plain mode is unchanged.** Only the Stop hook prints `late-child:`; the model's end-of-turn call keeps its one line.
- **`cancelled` counts as finished**, with `completed`, `failed` and `interrupted`.
- **A child with no thread in the store is skipped** by the hook; the tick already flags it `unread`.
- **The hook adds one read-only SQLite query per active child per stop.** Not measured; the store reads in the tick take milliseconds.
