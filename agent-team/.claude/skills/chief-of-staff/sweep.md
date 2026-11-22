# Sweep

Read this when the sweep exits 1 or 2, on a `merge-wait` or `run-wait` line (or a `merge-wait:` or `run-wait:` line from `cos_route.py`), or when take-over step 3.2 starts a merge wait.

## Sweep

A run started by `t3_thread_send` from a non-parent thread sends no finish notice; the ticket keeps its slot until the user writes.

`python3 ~/.collective-wisdom/scripts/cos_sweep.py --thread <this thread's id> --next` runs every check that needs no thread reads (merged check with `--apply`, ready, parent, untracked, review on `awaiting-review` tickets) and writes only what the merged check writes. Do what each `next:` line says, the last line's too. Flags, lines and exit codes: its docstring.

- It runs on every tick, after the child reads and the idle check, and in take over, `resume` and resume mode (rotation.md § Thread rotation "Take over" step 3.2); not elsewhere, and not on the turn that starts a helper.
- `ready`, `conflict`, `pushed` and `full` put a ticket on the `read in full:` list (a `conflict` ticket then gets § Conflict relay). `building`, `writing`, `no-pr` and `idle` (`--verbose` only) move nothing; `idle` matters to take-over step 4.
- `merged` lines: § Merged check. Review lines: review.md § Review check. `untracked` (nothing is read in full, written or started for it): the line's `next:` holds Sweep's drop (on Linear or Jira, `get-ticket`: drop it when labelled `agent-skip` or not In Progress or In Review; a child-thread title match needs `<PREFIX>-N` not followed by another digit) and the Needs you line.
- Exit 1 is not a failure. Exit 2 (Sweep's fallback): a part didn't run; the last line's `next:` gives each part's fallback and the Cleanup line.

## Conflict relay

After a `conflict` ticket's full read, its sweep line's `next:` holds the steps (the relay to the child, `conflictHead`, the run wait, the Moving line).

## Merged check

`cos_merged_check.py --apply` (sweep only) writes the `merged` op for a merged PR whose finish notice never arrived and so still holds the merge slot. A later finish notice finds no ticket and takes the generic path, as after `cancel N`. `mismatch` and `unreadable` write nothing: one Cleanup line. Exit 2: Sweep's fallback.

## Merge wait

On Cursor skip § Merge wait and § Run wait (`t3_background_wait` is refused there, G32) and ignore the `merge-wait` and `run-wait` plan and `cos_route.py` lines; the Stop hook's `late-child:` line, a user message or the next tick catches a lost notice. Never run these waits in the foreground (up to 110 minutes blocked).

A finish notice can be lost even for this thread's own child, and a ticket with no known parent thread gets none. `cos_merge_wait.py` (read only; polling in its docstring) starts for a `merge-wait <PREFIX>-N` plan line, a `merge-wait:` line of `cos_route.py`, a `fallback:` line that says so, and in take over and resume for each `merge` ticket whose `parentThreadId` is not this thread (rotation.md § Thread rotation "Take over" step 3.2).

1. Run `python3 ~/.collective-wisdom/scripts/cos_merge_wait.py <PREFIX>-N --next` with the Bash tool's background option (never `&`) and keep the task ID.
2. Call `t3_background_wait` on that ID once, just before the turn's last tool call (the rotation check stays last). On `unmatched`, start the command again and wait again; a second `unmatched` adds one Cleanup line, `Merge wait for <PREFIX>-N: <short title> did not start`.
3. When it exits the thread wakes: do what its `next:` line says.

Two waits on one ticket, merge or run, are harmless: both only read. Only the merged check writes the `merged` op.

## Run wait

`cos_run_wait.py` (read only; polling in its docstring) starts for a `run-wait <PREFIX>-N` plan line, a `run-wait:` line of `cos_route.py`, a `fallback:` line that says so, after a Todo or Backlog start (readiness.md § Todo start), a continuation child in the spec or build lane (continuation.md), and a stuck-check restart or an approvals.md send-back of a child that stays in `spec` or `build`.

1. On Cursor skip it (§ Merge wait, first paragraph). Otherwise start it as in § Merge wait steps 1 and 2, with `cos_run_wait.py <PREFIX>-N --next` and `timeout: 7200000` (the default is 30 minutes). A second `unmatched` adds the Cleanup line `Run wait for <PREFIX>-N: <short title> did not start`.
2. When it exits the thread wakes: do what its `next:` line says.
