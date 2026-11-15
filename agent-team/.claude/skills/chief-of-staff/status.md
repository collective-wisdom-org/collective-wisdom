# Chief of Staff: status

Read on `status` or `where's <PREFIX>-N?`.

## Answering status

Run the tick with `--trigger status` (SKILL.md § Tick): it reads every active child, runs the idle check and the sweep (sweep.md § Sweep). Then answer in the layout of `## Status layout` below. Post the full block again for each pending approval (approvals.md § Approval requests).

## Status layout

`status` and `where's <PREFIX>-N?` answer in this layout, not in the routine report shape of report-format.md § Report format. It is one small markdown table per group, under a bold header with the count. The user scans down one column for the ticket and one for the risk, and reads the next action in the third. Separate tables keep the group order and counts visible as headers. Unrendered, they still read line by line. While a No Hands run is active, the answer starts with the No Hands line (report-format.md § Report format).

```
**Awaiting merge approval (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-197** CSV export<br>[<PREFIX>-197](<thread link>) | High (touches auth) | PR #180, reviews PASS. Reply `approve 197`, or `changes 197: …`. |

**Speccing (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-240** Example feature<br>[<PREFIX>-240](<thread link>) | not rated yet | Spec since 14:05, no BUILD READY yet. |

**Building (2)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-199** Background jobs<br>[<PREFIX>-199](<thread link>) | Medium (changes slot fill, 4 Builds bullets) | PR #181, code review pass 2. |
| **<PREFIX>-154** Retry button<br>[<PREFIX>-154](<thread link>) | Low (docs only, 2 Builds bullets) | Restarted: stalled after code review PASS. |

**Queued to build (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-238** Export filters<br>[<PREFIX>-238](<thread link>) | Low (prose only, 3 Builds bullets) | Approved, waiting for a build slot. |

Filling stopped: lanes full.

<full merge block for <PREFIX>-197, as in approvals.md § Approval requests>
```

Groups, in this order, by stage:

| Group | Stages |
|---|---|
| Awaiting merge approval | `awaiting-merge` |
| Awaiting teammate review | `awaiting-review` |
| Merging | `merge` |
| Queued to merge | `merge-queued`, in the `queue merge:` order that `cos_state.py show` prints |
| Speccing | `spec` |
| Awaiting build approval | `awaiting-build` |
| Building | `build` |
| Queued to build | `build-queued`, in the `queue build:` order |
| Waiting to spec | `spec-queued` (in `queue spec:` order) |
| Other | `blocked` |

Rules:

- Empty groups drop out. The header count is the number of rows. Queued groups list tickets in the order they will start.
- The dashboard's Waiting to spec group also lists the Todo tickets after these (SKILL.md § Lanes, the spec queue). A `status` answer leaves them out: it makes no Todo read.
- Risk and detail come from the ticket's `status` line in state. The `Risk: …` tail is the Risk cell. The rest, shortened to what changed or what the user must do, is the detail. When the user has an action, the detail names the reply (`Reply "approve N"`, or for a blocked ticket the question to answer). An `Other` row says why it is there (`blocked: <reason>`). A `Waiting to spec` row says `[changes requested, ]waiting for a spec slot`.
- An `Awaiting teammate review` row's Next reads `PR #N, reviews PASS (CI green and CI review clean in ci mode). Waiting on <names>` (names from this turn's sweep `waiting` line, else the status line), plus `; your approval is held` when `heldApproval` is set.
- The Ticket cell is `**<PREFIX>-N** title`, then `<br>` and the link to the ticket's child thread (`childThreadId` in state). A row with no `childThreadId` (or a null one) has no `<br>` and no link. The link is never repeated in Next.
- The detail cell ends with `$X so far`, the dollar figure from one `python3 ~/.collective-wisdom/scripts/agent_usage.py --ticket <PREFIX>-N` per row, whatever the stage. A line starting `cost unknown` gives `cost unknown` instead. On exit 2 it adds nothing.
- Titles follow report-format.md § Report format (state first, then one `list-tickets` call with label `agent` and fields `id, title`). If none has it, show the ID alone.
- A `Merging` row's Next is `PR #N open, merge sent <time>` while this turn's merged check finds the PR open, never "merge in progress" from the relay alone.
- Anything this turn's idle check or sweep found goes in that ticket's detail (`merge ready, found by the sweep`). A ticket the sweep found merged has left state, so it gets one line below the tables: `Merged: <PREFIX>-190: Export page (#178)`. A ticket left as untracked after sweep.md § Sweep's drop gets one more: `Not in my state: <PREFIX>-125: Retry button (in review, #132); <PREFIX>-126: Search page (in progress).`
- After the tables comes the `Filling stopped:` line, then the full block for each pending approval (approvals.md § Approval requests), each with its risk on the first line.
- No other report-format.md § Report format section (`Moving`, `Running`, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`) appears in a `status` answer. A Cleanup item that came up waits for the next report.
- `where's <PREFIX>-N?` uses the same layout, with the thread link (a markdown link, report-format.md § Report format) under the ticket, and only that ticket's group and row, plus its full block if it waits on an approval. A ticket not in state (Todo, Backlog, merged, `agent-skip`) gets one line from the tracker: its state and title, or `merged (#PR)` from the `merged` list: `<PREFIX>-N: <short title>, merged (#PR)` (title: report-format.md § Report format).
