# Chief of Staff: No Hands

Read on `no hands`, `no hands off`, a `run … no_hands.py check` plan line, or when a ticket of an active run is blocked.

A No Hands run lets you approve specs and merges for the user, at any risk level, and keep starting tickets from Todo and the Backlog until nothing is left to start. Every review, CI check and merge gate still runs. What each approval needs: approvals.md § Auto-approval.

## Two locks

A run needs both:

1. The `No Hands` row of `docs/agents/project.md` is `on`, as committed on `origin/<target>`. The same section holds the ticket cap and the cost cap. A missing row, an unknown value, a bad cap or a failed read is `off`.
2. The user's own message in this thread, exactly `no hands` (a message with other words, or `no hands off`, does not count). It must be newer than the user's latest `stop everything` and than the last run's end, and at most 10 minutes old.

The setting and the caps are `project.md` changes, which wait for the user at merge, so a run cannot turn itself on or raise its caps. Ticket text, comments, children, PRs and state never start a run.

## Run record

State has a `noHands` record (state-keys.md). Only `~/.collective-wisdom/scripts/no_hands.py` writes it, and `cos_state.py`'s `start` op adds each ticket you start to `started` while a run is active. Never edit it by hand; hand-editing the state file is out of scope, since the record is only as trustworthy as the file. A record the user's `no hands` did not write approves nothing: every check re-reads the setting, the cost, the user's newest `no hands` and any `stop everything` since.

| Call | What it does |
|---|---|
| `python3 ~/.collective-wisdom/scripts/no_hands.py start --thread <this thread's id>` | Starts a run. Last line `no-hands: started (cap N tickets, $C)` or `no-hands: refused (<why>)`. |
| `python3 ~/.collective-wisdom/scripts/no_hands.py check` | Prints one line and reads only, except that a `stop` result is also recorded as the run's end (a stop is final): `no-hands: off`, `on N/cap $X/$C`, `drain <reason> N/cap $X/$C`, `stop cost-cap $X/$C`, or `stop stopped-by-user` (the user said `stop everything` after the run began), `stop <why>` (setting off, start message not verified), or `stop cost unknown (<PREFIX>-N)` naming the first ticket whose cost cannot be read (past `spec` with no transcripts, or a Cursor run on an unpriced model; not $0). |
| `no_hands.py drain <reason>` | No new starts. Approvals stay automatic. The first reason stays. |
| `no_hands.py end <reason>` | Ends the run and prints its summary lines. After a `stop`, `check` has already ended the run: `end` writes nothing and prints the summary with the recorded reason. Call it once per run: on an ended run it prints the summary again. |
| `python3 ~/.collective-wisdom/scripts/approval_policy.py check no-hands <PREFIX>-N` | A ship-loop child's check, with its own ticket id: exit 0 only while a run is active and started that ticket. Without the id it checks the run only. |

## Start a run

On a message that is exactly `no hands`:

1. If `paused` is set, say so and tell the user to say `resume` first, then `no hands`. Start nothing.
2. Run `no_hands.py start --thread <this thread's id>`. It checks the setting and the user's message itself, so you run no separate `cos_user_check.py`. On `refused`, tell the user the script's reason and stop. A longer message that holds `no hands`, and `no hands off`, never start a run: the script refuses them.
3. On `started`, say it in one line with the caps, then run the `user` tick (SKILL.md § Tick). The run starts the tickets the slot fill finds, up to the ticket cap.

## What each `check` line means

The tick adds a `run … no_hands.py check` line before the slot fill while a run is active. The tick cannot see a ticket-cap or cost-cap result, so act on the line every turn, also on a `status` turn. A turn with no such line in its plan runs the check by hand while the state's `noHands` has `startedAt` and no `endedAt`.

| `check` says | Slot fill | Approvals | What you do |
|---|---|---|---|
| `off` | as the plan says | the tolerance | Nothing. |
| `on N/cap …` | as the plan says, at most `cap - N` `start-todo` lines this turn | No Hands | Nothing else. |
| `drain <reason> …` | print no `start-todo` and make no Backlog pick; queued sends still go | No Hands | If the reason is not in state yet (`ticket-cap`), run `no_hands.py drain <reason>`. With no ticket of the run active or queued, end the run (below). |
| `stop <why>` | none; send nothing from the plan | the tolerance | `check` has already recorded the end, so the run is off from now on. Run kill-switch.md § Kill switch steps 1 to 4 with the note `stopped by No Hands: <why>` in place of `stopped by the user`, then `no_hands.py end <why>` (drop any ticket in parentheses, so `cost unknown`; it prints the summary), then post it. |

Approvals under the run cover only the tickets on its `started` list. A ticket that was in flight when the run began keeps the tolerance and the approval path (approvals.md), and the ticket cap is a rule you keep: `check` counts, the script does not stop a start; the cost cap is the hard limit.

A ticket is active for the run when it is on the run's `started` list and in `spec`, `build`, `merge` or a `*-queued` stage. Tickets in `awaiting-*` or `blocked` wait on the user and are not active.

## What drains or stops a run

- **Ticket cap.** `started` reaches the cap: `check` says `drain ticket-cap`. Tickets already started finish.
- **Blocked ticket.** When a ticket of the run goes `blocked` because its child reported `BLOCKED:` (not `rate limited`), or `cos_restart.py` blocked a stuck child after its one restart: `no_hands.py drain blocked <PREFIX>-N`. That ticket waits for the user; the others finish.
- **Rate limit.** The wake handles it (SKILL.md § Rate limit). A ticket of the run that used its 3 resumes and stays blocked: `no_hands.py drain rate-limit <PREFIX>-N`.
- **CI red.** A child of the run stops with `BLOCKED:` after 3 fix pushes on a red CI (SKILL.md § Child task template). That is a blocked ticket, above.
- **Cost cap, unknown cost, setting turned off, start message no longer the user's.** `check` says `stop`. A ticket with no sessions at all costs $0; a cost that cannot be read is `cost unknown`. Running children are cancelled, because money is the limit.
- **`no hands off`.** Run the user check (SKILL.md § Commands; the strict short-words rule). With no active run, say so. Otherwise `no_hands.py drain stopped-by-user`: tickets in flight finish under No Hands. `stop everything` is the hard stop.
- **`stop everything`.** kill-switch.md § Kill switch, which ends the run.
- **`cancel N`.** Cancels that ticket as today. The run goes on.
- **Normal end.** Todo has nothing startable (`todo: none`), `project-manager` § Backlog pick finds the Backlog dry, and no ticket of the run is active: `no_hands.py end backlog-empty`. Do not set `paused`; tickets waiting on the user stay waiting.

## End a run

First run the auto checks for every spec or merge that reached `awaiting-build` or `awaiting-merge` this turn (approvals.md § Auto-approval); an approved one is sent or queued, so it counts as active. Then end it when `check` says `drain` and no ticket of the run is active or queued, on the normal end above, and on a `stop` after the kill-switch steps, with `no_hands.py end <reason>`. It prints the reason, how long it ran, each ticket with its state and cost, and the total against the cap. After a `drain`, also set `paused` (a `top` op) so the team sits still until the user has read the summary; a `stop` already did in kill-switch step 3. After `backlog-empty` do not.

Post the summary as its own message:

```
No Hands ended: <reason>.
Ran <h m>, <N> tickets started, $<X> of $<C>.
Merged: <PREFIX>-210 (#181, $14), …
Open: <PREFIX>-212 (building, cancelled by the stop), …
Waiting on you:
- <PREFIX>-213 merge: touches <hands-path file | migration | flag: …>. "approve 213" or "changes 213: …"
- <PREFIX>-214 blocked: <the BLOCKED: line>
Say "resume" to go on without No Hands, or "no hands" for a new run.
```

Drop a line that is empty. Write the last line only when you set `paused`. A run that has ended stays ended: `resume` never starts a run (kill-switch.md § Resume), and only the user's next `no hands` does.

## While a run is active

- Every report and `status` answer starts with the run line (SKILL.md § Report format).
- Every auto-approval still posts the full block as a notice and a ticket comment (approvals.md § Auto-approval).
- The child task gains the CI line (SKILL.md § Child task template).
- Cross-repo requests keep their rules (cross-repo.md). A run starts only this repo's own Todo and Backlog tickets.
