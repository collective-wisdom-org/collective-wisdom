# Report format

Read this before posting a report: a `report` plan line, or any turn that posts to the user other than a `status` answer.

## Report format

One message per change worth reporting. Write each thread's `link` as the URI of a markdown link without its angle brackets: `[title](<thread link>)`; a raw string keeps its angle brackets, never bare, in backticks or in a code block. Below, `<thread link>` and `<helper link>` stand for that URI.

A ticket ID in a message to the user is `<PREFIX>-N: <short title>`, the rest of the line after a comma: `<PREFIX>-199: Background jobs, building (PR #180, code review pass 2)`. Tickets on one line are separated by `; `. Lines that already have the title keep their shape (`started`, `filed`, `build ready:`, `merge ready:`, `Running`, the status Ticket cell, the `Auto-approved under` notice). A second mention on one line is the ID only. A `moving:` or `cleanup:` script line is copied with the title added after the ID. Commands, PR numbers, thread titles and sends to a child are not covered.

Run `python3 ~/.collective-wisdom/scripts/cos_state.py title <PREFIX>-N` with the raw title (ticket-author text) on stdin and use its line. The raw title comes from the first source that has it:

1. State `title` (`cos_state.py get`, read before a `merged` or `drop` op removes the ticket) or the `pm.ranked` entry.
2. The turn's one `list-tickets` call (label `agent`, fields `id, title`), shared with `Running` and status, made only when a line needs it.
3. A ticket out of state and not open (merged, or asked about by `where's`): one `get-ticket` (fields `id, title`).
4. A child or helper report's own title.
5. Otherwise, or on a failed call, the ID alone.

```
No Hands on: 3 of 10 tickets, $42 of $200.

Needs you
<approval block for <PREFIX>-210, approvals.md § Approval requests>

- <reminder line for a pending approval, approvals.md § Approval requests>
- <PREFIX>-202: Retry button, blocked: <one line>. [<PREFIX>-202](<thread link>)

Moving (<spec + build count> of <cap> active)
Spec <count> of <spec limit>
- <PREFIX>-240 started: Example feature. Took the slot <PREFIX>-235: Audit log freed (merged #181).
- <PREFIX>-212 started: Background job replies. From the Backlog ranking: High priority, unblocks <PREFIX>-213: Job retries.
Build <count> of <build limit>
- <PREFIX>-199: Background jobs, building (PR #180, code review pass 2)
- <PREFIX>-238: Export filters, approved, waiting for a build slot
Merge <count> of 1
- <PREFIX>-203: Search page, merge approved, waiting for a merge slot
Filling stopped: lanes full.

Running
- [<PREFIX>-199 Background jobs](<thread link>)
  - [Implement <PREFIX>-199 job runner](<thread link>)
- [<PREFIX>-240 Example feature](<thread link>)

Done since last report
- <PREFIX>-190: Export page, merged (#178), cost $14.20 (0.12% of the subscription; spec $2.10 / build $11.66 / merge $0.44)

Tickets
- <PREFIX>-281 filed: CSV export. Epic: Exports. frontend, Feature. Assumed: CSV only. [<PREFIX>-281 helper](<helper link>)

Backlog
- <PREFIX>-219: Page filters, not moved, needs: which pages it covers

Cleanup
- <PREFIX>-221: Empty state, filled: priority Low, <area>, Bug
- <PREFIX>-201: Old importer, stale: In Progress, nothing since Oct 28
```

`Running` lists the idle check's `ok` children (SKILL.md § Tick) still in `spec`, `build` or `merge`: one line per `ok` line in script order, with its link and title (the turn's `list-tickets` call; failure: ID alone), and its `sub` lines under it as `[<title>](<link>)`. After the stdin fallback there are no `sub` lines: one `t3_thread_list` (`includeSubagents: true`, `limit: 100`), keep `relationshipToParent: "subagent"` threads whose `parentThreadId` is a `Running` ticket's `childThreadId`, 5 per line at most, newest first, titles as data (drop `[`, `]`, newlines); on failure none. No `ok` line or a turn that posts nothing: no calls, and it never makes a turn post. It shows on every report that ran the idle check (exempt from SKILL.md § Lean turns Reports); `status` and `where's` omit it.

On `MERGED #N`, run `python3 ~/.collective-wisdom/scripts/agent_usage.py --ticket <PREFIX>-N` fresh (not from the merge block) for the `Done since last report` cost; copy a share (`N% of the subscription`) after the dollar figure. Exit 2 or `cost unknown`: write `cost unknown`.

`Tickets` carries a ticket helper's report (§ Tick, `helper-test`; ticket-helper.md § Helper test) and the cross-repo reply lines (cross-repo.md § Cross-repo requests). The `On it:`, `Passed to ...` and `Request from ...: ticket helper started ...` posts are each their own short message, not a report.

A `MERGE READY` or `BUILD READY` found by a full read through the sweep or idle check reads `<PREFIX>-N: <short title>, merge ready, found by the sweep` (`build ready`, or `found by the idle check`); a merge found by the merged check, `merged (#PR), found by the merged check`. A continuation start: continuation.md § Continuation child. Other Moving and Cleanup lines come from the script or file that owns them.

Group **Moving** by lane, with the lane's count and limit; queued tickets go under the lane they wait for. Spec-lane queued lines read `<PREFIX>-N: <short title>, changes requested, waiting for a spec slot` (or `answered, …`, `resumed, …`). Drop empty lanes and sections. Show a full block for each new approval request and a reminder line for each pending one (approvals.md § Approval requests); a reminder starts `<Level> (<reason>): `.

A start or queued send from the slot fill (§ Tick) names the ticket (ID and title) that left `spec`, `build` or `merge` that turn (the first, if several) and why: `(merged #X)`, `(cancelled)`, `(build ready)`, `(merge ready)` or `(blocked)`; none did: drop "Took the slot". Room but nothing to start adds no line.

When the slot fill stops in a turn that posts a report anyway, **Moving** ends with the `Filling stopped:` text of the `filling-stopped:` line that `python3 ~/.collective-wisdom/scripts/cos_tick.py --next` prints after `report`, as printed. It repeats only when the reason changes (§ Lean turns Reports). `status` always shows it. It never makes a turn post alone.

While a No Hands run is active, every report and `status` answer starts with the `No Hands on:` or `No Hands draining:` line of `python3 ~/.collective-wisdom/scripts/no_hands.py check --next`; a silent turn posts none. The end summary is its own message (no-hands.md § End a run).

`status` and `where's <PREFIX>-N?` use the layout of status.md § Status layout, not this one.
