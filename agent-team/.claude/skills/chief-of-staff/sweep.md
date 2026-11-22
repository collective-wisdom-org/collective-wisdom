# Sweep

Read this when the sweep exits 1 or 2, on a `merge-wait` or `run-wait` line (or a `merge-wait:` or `run-wait:` line from `cos_route.py`), or when take-over step 3.2 starts a merge wait.

## Sweep

A run started by `t3_thread_send` from a non-parent thread sends no finish notice; the ticket keeps its slot until the user writes.

`python3 ~/.collective-wisdom/scripts/cos_sweep.py --thread <this thread's id> --next` runs every check that needs no thread reads (merged check with `--apply`, ready, parent, untracked, review on `awaiting-review` tickets) and writes only what the merged check writes. Do what each `next:` line says, the last line's too. Flags, lines and exit codes: the script's docstring.

- It runs on every tick, after the child reads and the idle check, and in take over, `resume` and resume mode (rotation.md § Thread rotation "Take over" step 3.2); not elsewhere, and not on the turn that starts a helper.
- `ready`, `conflict`, `pushed` and `full` lines put a ticket on the `read in full:` list. `conflict` is a `build` ticket whose PR conflicts with the merge target branch and has no checks, so CI cannot start: full read, § Child path (Conflict), then § Conflict relay. `building`, `writing`, `no-pr` and `idle` lines (`--verbose` only) move nothing (`idle` matters to take-over step 4); the ready check's `unreadable` is covered by the idle check.
- `merged` lines: § Merged check. The review check's lines (`approved`, `changes`, `moved`, `closed`, `unreadable`; `waiting` only with `--verbose`): review.md § Review check.
- `untracked` is a ticket in flight that state has never heard of: nothing is read in full, written or started for it. Sweep's drop: on Linear or Jira run `get-ticket` and drop the line when the ticket is labelled `agent-skip` or is not In Progress or In Review. A child-thread title match needs `<PREFIX>-N` not followed by another digit. The Needs you line is in the line's `next:`; it never makes a quiet turn post.
- Exit 1 is not a failure. Exit 2, a part didn't run (Sweep's fallback): the last line ends `; didn't run: <parts>` and its `next:` gives each part's fallback and the Cleanup line. Never say or imply nothing is waiting in the lanes that part covers.

## Conflict relay

A ticket listed with `conflict`, after its full read, still in `build` with no new marker. A `running` child: do nothing, its own CI wait sees the conflict (`ship-loop` § CI waits). Otherwise `t3_thread_send` the child at once `CHIEF OF STAFF: the PR conflicts with <target>. Resolve it per open-pr § Conflict resolution and report MERGE READY.` (the `CONFLICT` text of `cos_head_check.py`; `<target>` is the merge target branch). It keeps its build slot: no slot check, queue or `cos_route.py`, as for the stuck-check restart. Then a `set` op with `conflictHead` = the PR's full head (state-keys.md § State keys), start the run wait (§ Run wait), add the Moving line `<PREFIX>-N: <short title>, PR conflicts with <target>, sent back to resolve it`, and skip the stuck check for that ticket this turn.

## Merged check

A child can merge and its finish notice never arrive, leaving the ticket in `merge` and holding the only merge slot. `cos_merged_check.py --apply` finds those by PR number and branch and writes the `merged` op for each; it runs only as part of the sweep. A later finish notice finds no ticket and takes the generic path, as after `cancel N`. `mismatch` and `unreadable` write nothing: one Cleanup line. Exit 2: Sweep's fallback.

## Merge wait

On Cursor skip § Merge wait and § Run wait (`t3_background_wait` is refused there, G32) and ignore the `merge-wait` and `run-wait` plan lines and `cos_route.py` lines; the Stop hook's `late-child:` line, a user message or the next tick catches a lost notice. Never run these waits in the foreground (up to 110 minutes blocked).

A finish notice can be lost even when this thread is the parent, and a ticket with no known parent thread gets none. `cos_merge_wait.py` (read only) polls the PR every 30 s for 30 minutes. It starts for a `merge-wait <PREFIX>-N` plan line, a `merge-wait:` line of `cos_route.py`, a `fallback:` line that says so, and in take over and resume for each `merge` ticket whose `parentThreadId` is not this thread (rotation.md § Thread rotation "Take over" step 3.2).

1. Run `python3 ~/.collective-wisdom/scripts/cos_merge_wait.py <PREFIX>-N --next` with the Bash tool's background option (never `&`) and keep the task ID.
2. Call `t3_background_wait` on that ID once, just before the turn's last tool call (the rotation check stays last). On `unmatched`, start the command again and wait again; a second `unmatched` adds one Cleanup line, `Merge wait for <PREFIX>-N: <short title> did not start`.
3. When it exits the thread wakes: do what its `next:` line says.

Two waits on one ticket, merge or run, are harmless: both only read. Only the merged check writes the `merged` op.

## Run wait

A spec or build child's finish notice can be lost, leaving the ticket at `BUILD READY` or `MERGE READY`. `cos_run_wait.py` (read only) reads the child's newest run every 30 s for 110 minutes. It starts for a `run-wait <PREFIX>-N` plan line, a `run-wait:` line of `cos_route.py`, a `fallback:` line that says so, after a Todo or Backlog start (readiness.md § Todo start), a continuation child in the spec or build lane (continuation.md), and a stuck-check restart or an approvals.md send-back of a child that stays in `spec` or `build`.

1. On Cursor skip it (§ Merge wait, first paragraph). Otherwise start it as in § Merge wait steps 1 and 2, with `cos_run_wait.py <PREFIX>-N --next` and `timeout: 7200000` (the default is 30 minutes). A second `unmatched` adds the Cleanup line `Run wait for <PREFIX>-N: <short title> did not start`.
2. When it exits the thread wakes: do what its `next:` line says.
