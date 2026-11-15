# CW-406: Find a BUILD READY or MERGE READY soon after a child finishes, even when the finish notice is lost

**Status:** Draft
**Ticket:** [#406](https://github.com/collective-wisdom-org/collective-wisdom/issues/406)

## Goal

When a spec or build child ends its run at `BUILD READY`, `MERGE READY` or `BLOCKED:`, the Chief of Staff finds it within about a minute, even when T3's finish notice never arrives. And a child read finds that marker even when the child's newest message is a later short one with no marker.

## Today

- `cos_idle_check.py` flags `full <T> lost-notice` when a child's run is not running and the thread changed after `lastSeenAt`. It only runs on turns that already happen, so a lost notice waits for the next unrelated turn. Three sightings on 2026-11-15 (CW-380, CW-385, CW-371) sat 7 to 15 minutes.
- CW-386 starts a merge wait (`cos_merge_wait.py`, `sweep.md` § Merge wait) for every merge send. It polls GitHub and wakes the thread when the PR merges. Spec and build sends start nothing like it, and their end is not visible on GitHub: it is the child's run ending in T3.
- `cos_child_read.py` looks only at the newest finished assistant message of the newest run. When a child posts `MERGE READY` and then a short reply (for example to a stale restart notice, which starts a new run), the read prints `marker none` and a `tail:` of the short reply. CW-385 nearly read as "waiting on CI" this way.
- The Chief of Staff has no timer and no scheduled wake (CW-16). A background command that exits does wake it; the merge wait relies on that.

## Design

### 1. A run wait for every spec or build send

A new read-only script, `agent-team/scripts/cos_run_wait.py <PREFIX>-N [--file STATE] [--db PATH] [--every SECONDS] [--for SECONDS]`, shaped like `cos_merge_wait.py`. It is not a timer: it is one background command per send that ends when the child's run ends, the same kind of wake the merge wait already uses.

At start it reads the ticket from state (`cos_state.load`) and keeps its lane (`spec` or `build`), its `childThreadId`, and the child thread's newest run id and status from the T3 store (`~/.t3/userdata/statev2.sqlite`, opened `mode=ro`, as `cos_child_read.py` does). Then every 30 seconds, for up to 110 minutes:

1. Re-read the ticket. If it is gone, out of the lane, or has another `childThreadId`, print `run-wait: <T> left <lane>` and exit 0. This is the normal end when the finish notice did arrive: its tick has already moved the ticket.
2. Read the child's newest run. Keep waiting while it is `running`, and while it is still the run seen at start and that run was not running then (the send has not started a run yet).
3. A run that ended `failed`, `interrupted` or `cancelled`: print `run-wait: <T> run <status>` and exit 0.
4. A run that ended `completed`: look for a marker the way the child read does (§ 2), after the ticket's `lastPosition`. No marker (the child ended its turn on `t3_background_wait`, or stalled) means keep waiting: a background wait starts a new run when it ends, and a stall is the stuck check's job on the next tick.
5. A marker: wait one more round, re-read the ticket, and if it is still in the lane print `run-wait: <T> <BUILD READY|MERGE READY|BLOCKED|MERGED>` and exit 0. The extra round gives a late finish notice its turn first, so the usual case prints `left` and does nothing.
6. Time is up: `run-wait: <T> still working after 110m`, exit 1.
7. Exit 2, `run-wait: cannot <what>`: a bad ticket id, the ticket not in `spec` or `build` at the start, no `childThreadId`, unreadable state, or a store that is missing or not as expected.

110 minutes stays under the Bash tool's 2 hour cap on a background command. The Chief of Staff passes `timeout: 7200000` (the default is 30 minutes).

### 2. The child read finds an earlier marker

`cos_child_read.py` today takes the newest finished assistant message of the newest run. It changes to: when the newest run is `completed`, look at every finished assistant message after `--after`, newest first (across runs, so the restart-notice reply case is covered), and report the newest one that holds a marker. The `item=`, `marker`, `field`, `block:` and `cut` lines come from that message. `next=` stays the rank of the newest message, so `lastPosition` moves past both. With no marker in any of them, the output is as today (`marker none`, then `tail:` of the newest message).

The scan shares one function with `cos_run_wait.py`, so the wait and the read never disagree about whether a marker is there.

### 3. Who starts the wait

The wait starts after every send or start that puts a spec or build child to work, once the stage op is saved:

- `cos_route.py`: a `route: send spec` or `route: send build` prints `run-wait: <T>`, as a merge send prints `merge-wait: <T>`. The `fallback:` line of a spec or build continuation adds "and start the run wait".
- `cos_tick.py`: a `send <T> spec` or `send <T> build` plan line is followed by `run-wait <T>`.
- A Todo or Backlog start (`readiness.md` § Todo start), after its `start` op, and a continuation child in the spec or build lane (`continuation.md`), after its stage op.
- The stuck-check restart and the send-backs in `approvals.md` § Approval requests, when the child is in `spec` or `build`.

Two waits on one ticket are harmless: both only read, and the second tick's child read finds no new message.

### 4. When the wait ends

`sweep.md` gets a § Run wait next to § Merge wait, with the same steps:

- Run `python3 ~/.collective-wisdom/scripts/cos_run_wait.py <PREFIX>-N` with the Bash tool's background option and `timeout: 7200000`, and call `t3_background_wait` on its task ID once, just before the turn's last tool call. An `unmatched` ID is started again once; a second `unmatched` is one Cleanup line.
- A marker line or `run <status>`: run the tick with `--trigger 'notice:<childThreadId>'`, the same plan as the notice that never came (child read, idle check, sweep, slot fill). The child read finds the marker and the approval request goes out as usual.
- `still working after 110m`: run that tick once, then start a new wait if the ticket is still in the same lane with the same child.
- `left <lane>`: nothing.
- Exit 2, or no `run-wait:` line: one Cleanup line in the next report, `Run wait for <PREFIX>-N: <short title>, <its line>`.

### 5. Docs

- `SKILL.md`: a `run-wait <PREFIX>-N` row in § Tick; the `send` row says a spec or build send adds a `run-wait` line; the wake list (a run wait that ends); the Marker paragraph says the marker comes from the newest message after `lastPosition` that holds one; the files table row for `sweep.md`.
- `send-or-queue.md`: `route: send` copies a `run-wait:` line; the opening line names the `run-wait` plan line.
- `session.md`: `cos_run_wait.py` in the script list, and `t3_background_wait` for the run wait too.
- `readiness.md`, `continuation.md`: start the run wait, per § 3.
- Docstrings of `cos_route.py`, `cos_tick.py` and `cos_child_read.py`.

### 6. Tests

- `test_cos_run_wait.py`: one table-driven test of the decision per round (left the lane, still running, no run yet since the send, failed run, completed with no marker, completed with a marker and the grace round, time up), with a fake store and state, as `test_cos_merge_wait.py` does.
- `test_cos_child_read.py`: rows for a newest message with no marker after an earlier one that has one, in the same run and in an earlier run; and an earlier marker at or before `--after` that is not reported.
- `test_cos_route.py`: the send rows for the spec and build lanes print `run-wait:`; queue, continuation and merge rows do not.
- `test_cos_tick.py`: a queued spec approval's send is followed by `run-wait <T>`.

## Leaves out

- Changing how T3 sends finish notices, or why they are lost.
- A timer or scheduled wake (CW-16). The wait ends on the child's run, not on a clock, except the 110 minute cap.
- The merge lane (CW-386).
- A run wait for a child on another machine: the wait reads this machine's T3 store, as the child read and idle check already do.
- Running the tick on turns that run no tick today (ticket helper, team change).

## Calls I made

- The wait polls T3's local store, not GitHub. A spec or build child's end is a run ending in T3; GitHub shows a pushed spec or a PR, but not that the child stopped.
- The child read now scans every message after `lastPosition`, across runs, not only the newest run. The ticket's case (a reply to a stale restart notice) is a new run, so "same run only" would miss it. `lastPosition` keeps an old, already-handled marker from coming back.
- The wait keeps polling through a `completed` run with no marker, because that is usually a child waiting on CI. A child that truly stalled is left to the stuck check on the next tick, or to the 110 minute end, which runs the tick.
- A 110 minute window and a new wait after it, rather than one 30 minute wait like the merge one. A build run often takes over an hour, and a 30 minute wait would wake the Chief of Staff two or three times per build for nothing.
- One extra grace round (30 seconds) after a marker shows, so a finish notice that does arrive is handled first and the wait ends quietly.
- The wait also covers Todo and Backlog starts, continuations, the stuck-check restart and approval send-backs, not only `cos_route.py` sends. Any of them can end at a marker with a lost notice.
- One background store read every 30 seconds per spec or build child, up to the lane cap (4 by default).

## Acceptance

- A spec or build child that ends at `BUILD READY`, `MERGE READY` or `BLOCKED:` with no finish notice gets its approval request (or blocked report) within about a minute, with no user message.
- A child read of a thread whose newest message has no marker but an earlier one after `lastPosition` does reports that marker; `test_cos_child_read.py` has the same-run row the ticket asks for.
- `test_cos_route.py` has a row for a spec or build send that prints `run-wait:`.
