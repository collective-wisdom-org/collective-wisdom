# Chief of Staff: adopt

Read on `adopt N` (commands.md § Commands, strict check).

## Adopt

`adopt N` takes an untracked ticket into state.

1. Run `python3 ~/.collective-wisdom/scripts/cos_untracked_check.py`. Ticket not listed: say so, stop.
2. `get-ticket` (with `title`) and the adapter's author check. Untrusted author: say so, stop. On Linear or Jira also apply sweep.md § Sweep's drop (`agent-skip`, or not In Progress or In Review); dropped: say so, stop.
3. `t3_thread_list` for its child as in sweep.md § Sweep (the `<PREFIX>-N` title match applies).
   - Exactly one: read it, set the stage by startup.md § State rebuild (its `BUILD READY`, `MERGE READY` and unsure-is-`blocked` rules), write it with one `cos_state.py apply`: `start` (that thread's `parentThreadId`, the title from step 2), then `stage`. No title from step 2: write nothing, say it waits on the tracker. The parent check then lists it as `old-parent`.
   - More than one: list them, ask which, write nothing.
4. No child on this machine: write nothing. Say it can't be adopted here: run the team on the machine that owns it, or `cancel` it there and move it back to Todo.
5. Report under Moving: `<PREFIX>-N: <short title>, adopted at <stage>`. The turn's slot fill runs; a count over the cap is allowed (startup.md § State rebuild).
