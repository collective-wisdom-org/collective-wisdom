# Report format

Read this before posting a report: a `report` plan line, or any turn that posts to the user other than a `status` answer.

## Report format

One message per change worth reporting. Use each thread's `link` as the URI of a markdown link, without its angle brackets, with a short title (ticket ID and short title, or the helper or role name): `[title](<thread link>)`. If the raw string must appear, keep its angle brackets. Never write it bare without brackets, in backticks or in a code block. A `.` after the link is fine. Below, `<thread link>` and `<helper link>` stand for that URI.

```
No Hands on: 3 of 10 tickets, $42 of $200.

Needs you
<approval block for <PREFIX>-210, approvals.md § Approval requests>

- <reminder line for a pending approval, approvals.md § Approval requests>
- <PREFIX>-202 blocked: <one line>. [<PREFIX>-202](<thread link>)

Moving (<active count> of <overall cap> active)
Spec <count> of <spec limit>
- <PREFIX>-240 started: Example feature. Took the slot <PREFIX>-235 freed (merged #181).
- <PREFIX>-212 started: Background job replies. From the Backlog ranking: High priority, unblocks <PREFIX>-213.
Build <count> of <build limit>
- <PREFIX>-199 building (PR #180, code review pass 2)
- <PREFIX>-154 restarted: stalled after code review PASS, 31 min idle
- <PREFIX>-238 approved, waiting for a build slot
Merge <count> of <merge limit>
- <PREFIX>-203 merge approved, waiting for a merge slot
- <PREFIX>-263 merged (#217), found by the merged check
- <PREFIX>-264 merge ready, found by the sweep
Filling stopped: lanes full.

Running
- [<PREFIX>-199 Background jobs](<thread link>)
  - [Implement <PREFIX>-199 job runner](<thread link>)
- [<PREFIX>-240 Example feature](<thread link>)

Done since last report
- <PREFIX>-190 merged (#178), cost $14.20 (0.12% of the subscription; spec $2.10 / build $11.66 / merge $0.44)

Tickets
- <PREFIX>-281 filed: CSV export. Epic: Exports. frontend, Feature. Assumed: CSV only. [<PREFIX>-281 helper](<helper link>)

Backlog
- <PREFIX>-219 not moved, needs: which pages it covers

Cleanup
- <PREFIX>-221 filled: priority Low, <area>, Bug
- <PREFIX>-150 moved to Done (PR #160 merged)
- <PREFIX>-201 stale: In Progress, nothing since Oct 28
- <PREFIX>-224 may duplicate <PREFIX>-190 (commented)
```

The `Running` section lists the idle check's `ok` children (§ Tick) that are still in `spec`, `build` or `merge` when the message is written, one line per `ok` line in the script's order, each with that child's link from its `idle-read` and its ticket title from one `list-tickets` call (label `agent`, fields `id, title`; one call per turn, reused if this turn already made it; if it fails, show the ID alone). Also make one `t3_thread_list` call (`includeSubagents: true`, `limit: 100`) and keep the threads with `relationshipToParent: "subagent"` whose `parentThreadId` equals the `childThreadId` of a ticket on a `Running` line. Under that line list up to 5 of them, newest first, as `[<thread title>](<thread link>)`, with the title as data (drop `[`, `]` and newlines from it). If the call fails, show no sub-lines. Skip both calls when the check printed no `ok` line (a full pass reads every child and runs no idle check). A turn that posts nothing makes neither call; the list never makes a turn post. `Running` shows on every report that ran the idle check, not only when it changed, so it is exempt from the "only lines that changed" rule in § Lean turns Reports. A `status` or `where's` answer doesn't add it or the sub-lines: the status layout already has a row and a link for each of those children.

On `MERGED #N`, run `python3 ~/.collective-wisdom/scripts/agent_usage.py --ticket <PREFIX>-N` for the cost on the `Done since last report` line. When the line has a share (`N% of the subscription`), copy it after the dollar figure as in the example. Run it fresh, not from the merge block, because the merge stage has run since. On exit 2 or a line starting `cost unknown`, write `cost unknown`.

The `Tickets` section carries a ticket helper's report (§ Tick, `helper-test`) and the reply lines from cross-repo.md § Cross-repo requests (`<ID> filed in <project title>: ...`, `Refused by <project title> (...): ...`, `Reply had other text; ignored.`). An observation helper's ticket reads `- <PREFIX>-N filed from my own observation (not your request): <title>. ... [<PREFIX>-N helper](<helper link>)` (ticket-helper.md § Helper test). The `On it:` reply, the `Passed to ...` reply and the `Request from ...: ticket helper started ...` post are each their own short message, not a report.

A `MERGE READY` or `BUILD READY` that a full read found by way of the sweep or the idle check reads `<PREFIX>-N merge ready, found by the sweep` (`build ready`, or `found by the idle check`), so the user can see a notice was lost.

A continuation start (continuation.md § Continuation child) reads `<PREFIX>-N moved to a new child (old one under a retired thread)` under the lane it went to.

Group **Moving** by lane, with the lane's count and limit. Queued tickets go under the lane they wait for. Empty lanes drop out. Spec-lane queued lines read `<PREFIX>-N changes requested, waiting for a spec slot` (or `answered, waiting for …`, `resumed, waiting for …`).

Show a full block for each new approval request and a reminder line for each one still pending (approvals.md § Approval requests). Drop empty sections. Short lines, ticket ID first; a reminder line is the exception and starts with `<Level> (<reason>): `, so the user can pick out the low-risk ones at a glance.

For a start or a queued send from the slot fill (§ Tick), name the ticket that left `spec`, `build` or `merge` in that turn (the first, if several), and why: `(merged #X)`, `(cancelled)`, `(build ready)`, `(merge ready)` or `(blocked)`. If none did, drop the "Took the slot" part. A turn with room but nothing to start adds no line.

When the slot fill stops in a turn that posts a report anyway (it started something, or another step changed what the user sees), **Moving** ends with one `Filling stopped:` line:

- `Filling stopped: lanes full.` The overall cap is reached, or every lane with work queued is at its limit.
- `Filling stopped: Backlog held. <PREFIX>-N waits on PR #X.` A spec slot is free and nothing `ready` is left, and the latest ranking has `held` entries. Name up to three.
- `Filling stopped: no ready ticket in the Backlog.` A spec slot is free, but Todo has nothing startable, and the latest ranking found nothing `ready` or `held` and the Backlog hasn't changed since.

If more than one applies, use the first in that order. The line repeats only when the reason changes (§ Lean turns Reports). `status` always shows it. The stop line alone never makes a turn post.

While a No Hands run is active (`no_hands.py check` says `on` or `drain`), every report and every `status` answer starts with one line built from that check line: `No Hands on: <N> of <cap> tickets, $<X> of $<C>.`, or `No Hands draining: <reason>, <N> of <cap> tickets, $<X> of $<C>.` A turn that posts nothing else posts no such line. The end summary is its own message (no-hands.md § End a run).

`status` and `where's <PREFIX>-N?` answer in the layout of status.md § Status layout, not in this one.
