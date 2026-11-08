# Chief of Staff: adopt

Read on `adopt N` (SKILL.md § Commands, strict check).

## Adopt

`adopt N` takes a ticket the sweep listed as untracked into state.

1. Run `python3 ~/.collective-wisdom/scripts/cos_untracked_check.py`. If the ticket isn't listed (state has it now, or it left flight), say so and stop.
2. `get-ticket` (fields include `title`) with the adapter's author check. An untrusted author: say so and stop. On Linear or Jira also apply SKILL.md § Sweep's drop (`agent-skip`, or not In Progress or In Review) and, if it drops the ticket, say so and stop.
3. `t3_thread_list` for its child as in SKILL.md § Sweep (the `<PREFIX>-N` title match applies). Exactly one child thread: read it, set the stage by startup.md § State rebuild (the same `BUILD READY`, `MERGE READY` and unsure-is-`blocked` rules), and write it with one `cos_state.py apply` (`start` with that thread's `parentThreadId` and the ticket's `title` from step 2, then `stage`). No title from step 2 (read failed or blank): write nothing and say it can't be adopted until the tracker answers. The parent check then lists it as `old-parent` for a full read, as for any rebuilt ticket. More than one child thread: list them and ask which; write nothing.
4. No child thread on this machine: write nothing. Say it can't be adopted here, and that the user can run the team on the machine that owns it, or `cancel` it there and move it back to Todo to restart it.
5. Report under Moving: `<PREFIX>-N adopted at <stage>`. The turn's slot fill runs; the stage may put the count over the cap, which startup.md § State rebuild already allows.
