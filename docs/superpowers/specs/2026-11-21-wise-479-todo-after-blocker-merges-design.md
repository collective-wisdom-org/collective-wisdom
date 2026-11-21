# WISE-479: Mark tickets Todo when their last blocker merges

**Status:** Shipped
**Ticket:** [#479](https://github.com/collective-wisdom-org/collective-wisdom/issues/479)
**Shipped:** in PR #481, with differences: [as-built](../as-built/2026-11-21-wise-479-todo-after-blocker-merges.md)

## Goal

When a ticket merges, the Chief of Staff moves every Backlog ticket that the merge left with no open blocker to Todo. The ticket then joins the spec queue on its own, without the user pressing Start shipping.

## Today

- A merge ends in a `merged` op in `cos_state.py`, from one of two paths: the child's `MERGED #N` marker (chief-of-staff `SKILL.md` § Child path "Marker"), or a `merged` line of `cos_merged_check.py --apply` in the sweep (`sweep.md` § Merged check). The turn's slot fill then runs with `(merged #X)` as the reason.
- Nothing reads what the merged ticket was blocking. A blocked Backlog ticket stays in Backlog until the user moves it.
- `cos_todo.py` already has the blocker rule: `blockers(got)` reads `relations.blockedBy` (and its other spellings) and `is_open(b)` counts a blocker open unless its state is Done, Canceled or Duplicate.
- The adapters read what a ticket blocks: on GitHub `.../issues/N/dependencies/blocking` (`trackers/github.md` § `get-ticket`), on Linear the issue relations, on Jira the outward `Blocks` links.
- `org-chart.md` says the user moves tickets to Todo, and `readiness.md` § Todo start calls Todo "the user's queue".

## Change

### 1. `agent-team/scripts/cos_unblocked.py` (new)

A read-only script, in the shape of `cos_todo.py --relations`. It writes nothing and calls no tracker.

Stdin: `{"merged": "<PREFIX>-M", "tickets": {"<PREFIX>-N": <get-ticket JSON>}}`, one entry per ticket the merged ticket blocked. Each get-ticket result has `id, state, labels, relations`, with each blocker's state filled in, as `readiness.md` § Todo start already reads them. A ticket whose author the adapter calls untrusted is given as `{"untrusted": true}`.

For each ticket, in id order, it prints one line:

- `todo <ID>`: the ticket is in Backlog (`pm_hygiene.state_of`), not labelled `agent-skip`, not untrusted, and every blocker other than the merged ticket is closed (`cos_todo.is_open`). The merged ticket counts as closed whatever state the read gave it, since the tracker may not have caught up with the merge yet. A blocker matches the merged ticket by its id, or by its number alone when the read gives only a number (GitHub).
- `stay <ID> <why>`, where `<why>` is one of `state <State>`, `agent-skip`, `untrusted`, or `blocked by <ID>[, <ID>...]` (the blockers still open).

Then `unblocked: <C> checked, <T> to Todo`. Exit 0. Exit 2 with `unblocked: cannot <what>` when stdin is not usable (bad JSON, no `merged`, `tickets` not an object, an entry not an object). An empty `tickets` is fine: `unblocked: 0 checked, 0 to Todo`.

It reuses `cos_todo.blockers`, `cos_todo.is_open`, `pm_hygiene.state_of` and `pm_hygiene.labels_of`, so there is one rule for "open blocker" and one for "state".

### 2. Chief of Staff: `readiness.md` § Unblocked after a merge (new section)

After each `merged` op, on either path, and before the turn's slot fill:

1. `get-ticket` the merged ticket for what it blocks (GitHub: `.../issues/M/dependencies/blocking --jq '[.[].number]'`; Linear and Jira: their relations). None: stop here, no output.
2. `get-ticket` each blocked ticket (fields `id, state, labels, relations`, blocker states as § Todo start reads them, and the author check on GitHub). Give the results to `python3 ~/.collective-wisdom/scripts/cos_unblocked.py`.
3. For each `todo <ID>` line, `set-state` Todo. Report it under Moving, in the Spec lane: `<PREFIX>-N: <short title>, moved to Todo: last blocker <PREFIX>-M merged`. `stay` lines are not reported.
4. A failed read in step 1 or 2, or exit 2 from the script, adds one Cleanup line, `<PREFIX>-M: <short title>, could not read the tickets it blocked; none moved to Todo`, and nothing moves. A failed `set-state` adds one Cleanup line for that ticket. Neither stops the merge closeout, the rest of the turn or the slot fill.

The slot fill that follows (§ Todo start) then sees the moved tickets in its Todo list, so one can start in the same turn. Starting them stays with the existing slot fill.

### 3. Hook the two merge paths

- chief-of-staff `SKILL.md` § Child path, the `MERGED #N` bullet: after the `merged` op, readiness.md § Unblocked after a merge.
- `sweep.md` § Merged check, the `merged` line: the same.
- `SKILL.md`'s reading table row for `readiness.md` gains "after a `merged` op".

### 4. Docs that say only the user moves to Todo

- `docs/agents/org-chart.md`: the user row keeps "Moves tickets to Todo"; the Chief of Staff row's tracker writes add "moves a Backlog ticket to Todo when its last blocker merges".
- `readiness.md` § Todo start: "Todo is the user's queue" becomes "Todo is the user's queue (plus the tickets § Unblocked after a merge moves there)".
- `report-format.md` example: one Spec-lane line showing the new Moving line.

### 5. Test

`agent-team/scripts/test_cos_unblocked.py`: one table-driven test of the selection rule, run through the script's stdin and stdout. Rows:

| Ticket | Input | Line |
|---|---|---|
| B | Backlog, blocked by A only (A open in the read) | `todo B` |
| C | Backlog, blocked by A and D, D open | `stay C blocked by D` |
| E | Backlog, blocked by A, labelled `agent-skip` | `stay E agent-skip` |
| F | In Progress, blocked by A | `stay F state In Progress` |
| G | `{"untrusted": true}` | `stay G untrusted` |
| H | GitHub shape: open issue, no `status:` label, blockers as `{number, state}` with A's number only | `todo H` |

Plus one row for bad stdin exiting 2. "A Backlog ticket never blocked by the merged ticket is left alone" holds by construction: step 1 only reads what the merged ticket blocks, so such a ticket never reaches the script.

## Not changing

- `cos_todo.py`, the slot fill and § Readiness check: they already start Todo tickets.
- Tickets not blocked by the merged ticket. No bulk Backlog move.
- Tickets in any state other than Backlog.
- `cos_state.py` and `cos_merged_check.py`: the state file has no new key, and the merged check still only writes the `merged` op.
- `project-manager` and its "No Todo moves" rule: the move is the Chief of Staff's, not the project manager's.

## Acceptance

- B blocked by A only: A merges, B moves Backlog to Todo, and the next report lists it under Moving.
- C blocked by A and D: A merges with D open, C stays in Backlog.
- A blocked ticket labelled `agent-skip` stays in Backlog.
- A Backlog ticket not blocked by A is not read or moved.
- A failed read of what A blocked leaves the merge closeout and slot fill running and adds one Cleanup line.
- Both merge paths (`MERGED #N` and the sweep's `merged` line) run it.
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/cos_unblocked.py` | New: the selection rule |
| `agent-team/scripts/test_cos_unblocked.py` | New: table-driven test |
| `agent-team/.claude/skills/chief-of-staff/readiness.md` | § Unblocked after a merge; § Todo start wording |
| `agent-team/.claude/skills/chief-of-staff/SKILL.md` | `MERGED #N` bullet, reading table row |
| `agent-team/.claude/skills/chief-of-staff/sweep.md` | § Merged check `merged` line |
| `agent-team/.claude/skills/chief-of-staff/report-format.md` | Example Moving line |
| `agent-team/docs/agents/org-chart.md` | Chief of Staff row |

## Calls I made

- **The merged ticket counts as closed even if the read says open.** Right after a merge the GitHub issue may still be open (a `Closes #N` into a non-default branch, or a read that races the close), and Linear may lag. Without this, B would wrongly stay in Backlog.
- **It also runs while the team is paused (`stop everything`).** A Todo move only queues a ticket; nothing starts while paused, so the user's pause still holds. Skipping it would leave the ticket in Backlog for good, since nothing re-checks later.
- **The move happens before the turn's slot fill**, so a freed spec slot can take the newly Todo ticket in the same turn.
- **A new script, not a third mode of `cos_todo.py`.** The input and output differ (one merged ticket and its dependants, not the Todo list), and `cos_todo.py`'s first pass saves the dashboard list, which this must not do. It imports `cos_todo`'s blocker helpers instead of copying them.
- **The untrusted-author check stays in the adapter.** The Chief of Staff passes `{"untrusted": true}` for such a ticket so the rule and its test cover it, and the script never sees that ticket's text.
- **`stay` lines are not reported** to keep the report short; only moves and failures show.
- **The Moving line sits in the Spec lane**, where Todo tickets wait, as report-format.md groups queued tickets under the lane they wait for.
- **No comment on the moved ticket.** The report line is the record, and the tracker's own history shows the state change.
