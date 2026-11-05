# Chief of Staff: status

Read on `status` or `where's <PREFIX>-N?`.

## Answering status

Unless this turn's full pass already read every active child, run the idle check (SKILL.md § Lean turns) and the sweep (SKILL.md § Sweep), then answer in the layout of `## Status layout` below. Post the full block again for each pending approval (approvals.md § Approval requests).

## Status layout

`status` and `where's <PREFIX>-N?` answer in this layout, not in the routine report shape of SKILL.md § Report format. It is one small markdown table per group, under a bold header with the count. The user scans down one column for the ticket and one for the risk, and reads the next action in the third. Separate tables keep the group order and counts visible as headers. Unrendered, they still read line by line.

```
**Awaiting merge approval (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-197** CSV export<br><thread link> | High (touches auth) | PR #180, reviews PASS. Reply `approve 197`, or `changes 197: …`. |

**Building (2)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-199** Background jobs<br><thread link> | Medium (changes slot fill, 4 Builds bullets) | PR #181, code review pass 2. |
| **<PREFIX>-154** Retry button<br><thread link> | Low (docs only, 2 Builds bullets) | Restarted: stalled after code review PASS. |

**Queued to build (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-238** Export filters<br><thread link> | Low (prose only, 3 Builds bullets) | Approved, waiting for a build slot. |

**Other (1)**

| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-240** Example feature<br><thread link> | not rated yet | Spec stage since 14:05, no SPEC READY yet. |

Filling stopped: lanes full.

<full merge block for <PREFIX>-197, as in approvals.md § Approval requests>
```

Groups, in this order, by stage:

| Group | Stages |
|---|---|
| Awaiting merge approval | `awaiting-merge` |
| Merging | `merge` |
| Queued to merge | `merge-queued`, in the `queue merge:` order that `cos_state.py show` prints |
| Awaiting build approval | `awaiting-spec` |
| Building | `build` |
| Queued to build | `build-queued`, in the `queue build:` order |
| Other | `spec`, `spec-queued` (in `queue spec:` order), `blocked` |

Rules:

- Empty groups drop out. The header count is the number of rows. Queued groups list tickets in the order they will start.
- Risk and detail come from the ticket's `status` line in state. The `Risk: …` tail is the Risk cell. The rest, shortened to what changed or what the user must do, is the detail. When the user has an action, the detail names the reply (`Reply "approve N"`, or for a blocked ticket the question to answer). An `Other` row says why it is there (`spec stage`, `blocked: <reason>`, `changes requested, waiting for a spec slot`).
- The Ticket cell is `**<PREFIX>-N** title`, then `<br>` and the link to the ticket's child thread (`childThreadId` in state). A row with no `childThreadId` (or a null one) has no `<br>` and no link. The link is never repeated in Next.
- The detail cell ends with `$X so far`, the dollar figure from one `python3 scripts/agent_usage.py --ticket <PREFIX>-N` per row, whatever the stage. On exit 2 it adds nothing.
- Titles come from the tracker: one `list-tickets` call with label `agent` and fields `id, title`. If that read fails, show the ID alone.
- Anything this turn's idle check or sweep found goes in that ticket's detail (`merge ready, found by the sweep`). A ticket the sweep found merged has left state, so it gets one line below the tables: `Merged: <PREFIX>-190 (#178)`.
- After the tables comes the `Filling stopped:` line, then the full block for each pending approval (approvals.md § Approval requests), each with its risk on the first line.
- No other SKILL.md § Report format section (`Moving`, `Running`, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`) appears in a `status` answer. A Cleanup item that came up waits for the next report.
- `where's <PREFIX>-N?` uses the same layout, with the thread link under the ticket, and only that ticket's group and row, plus its full block if it waits on an approval. A ticket not in state (Todo, Backlog, merged, `agent-skip`) gets one line from the tracker: its state and title, or `merged (#PR)` from the `merged` list.
