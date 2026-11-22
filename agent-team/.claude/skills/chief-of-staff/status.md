# Chief of Staff: status

Read on `status` or `where's <PREFIX>-N?`.

## Answering status

Run the tick with `--trigger status` (SKILL.md § Tick): it reads every active child, runs the idle check and the sweep (sweep.md § Sweep). Then run `python3 ~/.collective-wisdom/scripts/cos_status.py --sweep "<the sweep's last line>"` (`--ticket <PREFIX>-N` for `where's`) and answer in the layout it prints (§ Status layout). Post the full block again for each pending approval (approvals.md § Approval requests).

## Status layout

`status` and `where's <PREFIX>-N?` answer in `cos_status.py`'s layout, not report-format.md § Report format: one small table per group under a bold header with the count, in the group order, with the Ticket and Risk cells and `$X so far` filled from state. Its docstring owns the layout. While a No Hands run is active the answer starts with the No Hands line (report-format.md § Report format). You add:

- Shorten each Next cell to what changed or what the user must do. When the user has an action it names the reply (`Reply "approve N"`, or for a blocked ticket the question to answer). An `Other` row says why (`blocked: <reason>`). A `Waiting to spec` row says `[changes requested, ]waiting for a spec slot`.
- An `Awaiting teammate review` row's Next reads `PR #N, reviews PASS (CI green and CI review clean in ci mode). Waiting on <names>` (names from this turn's sweep `waiting` line, else the status line), plus `; your approval is held` when `heldApproval` is set.
- A `Merging` row's Next is `PR #N open, merge sent <time>` while this turn's merged check finds the PR open, never "merge in progress" from the relay alone.
- What this turn's idle check or sweep found goes in that ticket's detail (`merge ready, found by the sweep`).
- A row with no title in state: one `list-tickets` call (label `agent`, fields `id, title`), titled as report-format.md § Report format says; else the ID alone.
- The `Merged:` line (a ticket the sweep found merged) and the `Not in my state:` line (an untracked ticket left after sweep.md § Sweep's drop) come from `--sweep` with IDs and PR numbers only. Add each ticket's title and, for `Not in my state`, its tracker state (`<PREFIX>-125: Retry button (in review, #132)`).
- After the tables: the `Filling stopped:` line (report-format.md § Report format), then the full block for each pending approval (approvals.md § Approval requests), each with its risk on the first line.
- The dashboard's Waiting to spec group also lists the Todo tickets (SKILL.md § Lanes); a `status` answer makes no Todo read and leaves them out.
- No other report-format.md § Report format section (`Moving`, `Running`, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`) appears. A Cleanup item that came up waits for the next report.
- `where's <PREFIX>-N?` shows only that ticket's group and row, with its full block if it waits on an approval. A ticket not in state (Todo, Backlog, merged, `agent-skip`) gets one line from the tracker: its state and title, or `<PREFIX>-N: <short title>, merged (#PR)` from the `merged` list.
