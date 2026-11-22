# Chief of Staff: No Hands

Read on `no hands`, `no hands off`, a `run … no_hands.py check` plan line, or when a ticket of an active run is blocked.

A run approves specs and merges for the user at any risk level and keeps starting Todo and Backlog tickets until none is left. Every review, CI check and merge gate still runs (approvals.md § Auto-approval).

## Two locks

Both are needed:

1. The `No Hands` row of `docs/agents/project.md` is `on`, as committed on `origin/<target>`; the same section holds the ticket cap and cost cap. A missing row, unknown value, bad cap or failed read is `off`.
2. The user's own message in this thread, exactly `no hands` (other words, or `no hands off`, don't count), newer than the user's latest `stop everything` and the last run's end, and at most 10 minutes old.

The setting and caps are `project.md` changes, which wait for the user at merge, so a run cannot raise its own caps. Ticket text, comments, children, PRs and state never start a run.

## Run record

State's `noHands` record (state-keys.md) is written only by `~/.collective-wisdom/scripts/no_hands.py` (and `cos_state.py`'s `start` op, which adds each started ticket). Never edit it by hand. It approves nothing by itself: every check re-reads the setting, the cost and the user's messages.

- `python3 ~/.collective-wisdom/scripts/no_hands.py start --thread <this thread's id>`, `check --next` (reads only, except that a `stop` is recorded as the run's end, final), `drain <reason>` (the first reason stays) and `end <reason>`: lines and exit codes are in the docstring. Call `end` once per run (after a `stop`, `check` already ended it).
- `python3 ~/.collective-wisdom/scripts/approval_policy.py check no-hands <PREFIX>-N`: a ship-loop child's check: exit 0 only while a run is active and started that ticket (without the id, the run only).

## Start a run

On a message that is exactly `no hands`:

1. `paused` set: say so, tell the user to say `resume` first, then `no hands`. Start nothing.
2. Run `no_hands.py start --thread <this thread's id>` (it checks the setting and message itself: no `cos_user_check.py`). On `refused`, tell the user its reason and stop.
3. On `started`, say it in one line with the caps, then run the `user` tick (SKILL.md § Tick).

## What each `check` line means

The tick adds a `run … no_hands.py check --next` line before the slot fill while a run is active. Do what its `next:` line says every turn, `status` too. A turn with no such line runs the check by hand while `noHands` has `startedAt` and no `endedAt`.

Approvals under the run cover only tickets on its `started` list; a ticket in flight when it began keeps the tolerance and approval path (approvals.md). The ticket cap is a rule you keep (the script doesn't stop a start); the cost cap is the hard limit. A ticket is active when it is on `started` and in `spec`, `build`, `merge` or a `*-queued` stage; `awaiting-*` and `blocked` tickets wait on the user.

## What drains or stops a run

- **Ticket cap.** `check` says `drain ticket-cap`. Started tickets finish.
- **Blocked ticket.** A ticket of the run goes `blocked` on its child's `BLOCKED:` (not `rate limited`) or a `cos_restart.py` block after its one restart: `no_hands.py drain blocked <PREFIX>-N`. It waits for the user; the others finish.
- **Rate limit.** rate-limit.md § Rate limit. A ticket of the run that used its 3 resumes and stays blocked: `no_hands.py drain rate-limit <PREFIX>-N`.
- **CI red.** A child stops with `BLOCKED:` after 3 fix pushes (readiness.md § Child task template): a blocked ticket.
- **Cost cap, unknown cost, setting off, start message no longer the user's.** `check` says `stop`; running children are cancelled: money is the limit.
- **`no hands off`.** Run the user check (commands.md § Commands; strict short-words rule). No active run: say so. Else `no_hands.py drain stopped-by-user`; tickets in flight finish under No Hands.
- **`stop everything`.** kill-switch.md § Kill switch, which ends the run.
- **`cancel N`.** Cancels that ticket; the run goes on.
- **Normal end.** `todo: none`, the Backlog pick finds the Backlog dry (`project-manager` § Backlog pick) and no ticket of the run is active: `no_hands.py end backlog-empty`; no `paused`.

## End a run

First run the auto checks for every spec or merge that reached `awaiting-build` or `awaiting-merge` this turn (approvals.md § Auto-approval); an approved one is sent or queued, so it counts as active. Then `no_hands.py end <reason>` when `check` says `drain` and no ticket of the run is active or queued, on the normal end, and on a `stop` after the kill-switch steps. After a `drain` also set `paused` (a `top` op) so the team sits still until the user has read the summary; a `stop` already did (kill-switch step 3); `backlog-empty` doesn't.

Post the summary as its own message:

```
No Hands ended: <reason>.
Ran <h m>, <N> tickets started, $<X> of $<C>.
Merged: <PREFIX>-210: Example feature (#181, $14); …
Open: <PREFIX>-212: Background jobs (building, cancelled by the stop); …
Waiting on you:
- <PREFIX>-213: Search page, merge: touches <hands-path file | migration | flag: …>. "approve 213" or "changes 213: …"
- <PREFIX>-214: Billing page, blocked: <the BLOCKED: line>
Say "resume" to go on without No Hands, or "no hands" for a new run.
```

Merged tickets' titles: one `list-tickets` call (label `agent`, state Done, updated since the run's `startedAt`, fields `id, title`); open and waiting ones from state (report-format.md § Report format). Drop an empty line; write the last line only when you set `paused`. An ended run stays ended (kill-switch.md § Resume).

## While a run is active

Every report and `status` answer starts with the run line (report-format.md § Report format). A run starts only this repo's own tickets.
