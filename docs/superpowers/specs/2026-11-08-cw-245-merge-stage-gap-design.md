# CW-245: Close the gap between a merge and the ticket leaving the merge stage

**Status:** Shipped
**Shipped:** in PR #249, with differences: [as-built](../as-built/2026-11-08-cw-245-merge-stage-gap.md)
**Ticket:** [#245](https://github.com/collective-wisdom-org/collective-wisdom/issues/245)

## Goal

When a merge runs in a child the Chief of Staff will not hear from, state moves the ticket out of `merge` within about a minute of the PR merging, with no user message, so the merge slot frees and the next queued merge starts. The dashboard never lists a ticket both under a status group and under merged.

## Today

Facts from `main` at `6cdfe6c`.

- T3 sends no run-finished notice for a run started by `t3_thread_send` from a thread that isn't the child's parent (`chief-of-staff/SKILL.md` § Sweep). Every place that sends to such a child adds the Moving line `<PREFIX>-N: I may not hear when this run ends; say status to check.`: the tick's `send` line (`cos_tick.py` `relay_lines`), the `moving:` line of `cos_route.py`, and its `fallback:` line, for a continuation that falls back to the old child (`continuation.md`).
- After a rotation, take over (`rotation.md` step 4) runs the idle-check reads, the sweep and the slot fill once. A ticket whose merge is still running under the old thread stays in `merge` until a later tick.
- Only the sweep's merged check (`cos_merged_check.py --apply`) writes the `merged` op without a child report. The sweep runs on every tick, and a tick runs only on a user message, a child notice, a cross-repo message, `start` or the rate-limit wake. Nothing runs a tick soon after a merge nobody reports.
- The Chief of Staff has Bash. A child already waits on long commands by running them in the background and calling `t3_background_wait`, which wakes the thread when the command exits (`ship-loop` § Run endings).
- The dashboard builds `status` from state with `groupTickets` (`count` is `rows.length`, empty groups dropped) and `merged` from GitHub (`merged.ts`, each entry with `id` and PR `number`). `buildApi` (`dashboard/api.ts`) never compares them.

## Design

Both fixes from the ticket. The merge wait closes the gap in state; the dashboard filter hides what is left of it (the merge wait's poll interval, and any wait that never started).

### 1. `cos_merge_wait.py`

A new read-only script: `python3 ~/.collective-wisdom/scripts/cos_merge_wait.py <PREFIX>-N [--file STATE] [--every SECONDS] [--for SECONDS]`. Defaults: every 30 seconds, for 30 minutes.

Each round it reads state through `cos_state.load` and, while the ticket is still in `merge` with an integer `pr`, runs `~/.collective-wisdom/scripts/gh.sh pr view <pr> --json state` (20 second timeout). Its last line and exit code:

| Line | Exit | When |
|---|---|---|
| `merge-wait: <PREFIX>-N #PR merged` | 0 | GitHub says `MERGED` |
| `merge-wait: <PREFIX>-N #PR closed` | 0 | GitHub says `CLOSED` |
| `merge-wait: <PREFIX>-N left merge` | 0 | the ticket is gone from state or no longer in `merge` (a notice or `cancel N` got there first) |
| `merge-wait: <PREFIX>-N #PR still open after <M>m` | 1 | the time ran out |
| `merge-wait: cannot <what>` | 2 | a bad ticket id, no such ticket at the start, no integer `pr`, unreadable state, or 5 GitHub reads in a row that failed or gave bad JSON |

It writes nothing: the merged check stays the only writer of the `merged` op, and it checks the PR's branch, which the wait does not. The decision for one round is a pure function (`decide(ticket, gh_result) -> line, exit | None`) so the test needs no sleeping; the loop takes an injectable clock and sleep.

### 2. When the Chief of Staff starts it

The rule: wherever the "I may not hear" line goes out for a send in the **merge** lane, a merge wait starts for that ticket. The scripts print it, so the model doesn't have to remember:

- `cos_tick.py` `relay_lines`: after a `send <PREFIX>-N merge …` line whose ticket's `parentThreadId` is not this thread, it prints `merge-wait <PREFIX>-N`.
- `cos_route.py`: a `route: send merge` that prints a `moving:` line also prints `merge-wait: <PREFIX>-N`. A `route: continuation merge` adds to its `fallback:` line: `and start the merge wait`.
- Take over and resume (`rotation.md` step 4, a new sub-step after the sweep): for each ticket still in `merge` whose `parentThreadId` is not this thread, start a merge wait. This is the CW-238 and CW-240 case: the merge was running under the old thread when it rotated.

What "start a merge wait" means, in SKILL.md (a new § Merge wait, and a `merge-wait <PREFIX>-N` row in the § Tick plan-line table):

1. Run `python3 ~/.collective-wisdom/scripts/cos_merge_wait.py <PREFIX>-N` with the Bash tool's background option (never `&`). Keep the task ID.
2. Call `t3_background_wait` on that ID once, just before the turn's last tool call (the rotation check stays last). If the wait lists the ID under `unmatched`, start the command again once and wait again; a second `unmatched` adds one Cleanup line, `Merge wait for <PREFIX>-N did not start`.
3. When it exits, the thread wakes. On `merged` or `closed`, run the tick with `--trigger 'notice:<childThreadId>'`, the ticket's child from `cos_state.py get <PREFIX>-N`: the same plan as the finish notice that never came (child read, idle check, sweep with the merged check, slot fill). On `still open`, run the same tick once and start no new wait; the Moving line already told the user to say `status`. On `left merge`, nothing: no tick, no message. On exit 2, one Cleanup line in the next report, `Merge wait for <PREFIX>-N: <its line>`, and nothing else.

`notice:` already takes any thread id and skips the read when the ticket is in no active stage, so `cos_tick.py` needs no new trigger. The skill's description line ("Acts only on …") and § Tools add the merge wait.

A retired thread whose merge wait ends does nothing but its `Moved to` reply (new row in `rotation.md` § Thread rotation: Retired thread); its successor started its own wait at take over. Two waits on one ticket are harmless: both are read only, and the second tick finds the ticket already gone.

### 3. Dashboard: merged wins

In `buildApi`, a status row is dropped when `merged` has an entry with the row's ticket id and `number` equal to the ticket's state `pr`. Group `count` is recomputed from the rows that remain, and a group left empty is dropped, as `groupTickets` does. Matching on both id and PR number keeps a ticket whose earlier PR merged and that now has a new one in flight. `merged` itself is unchanged.

## Tests

- `test_cos_merge_wait.py`, one table-driven test of `decide`: merged, closed, open, ticket left `merge`, ticket gone, no `pr`, bad JSON. One loop test with a fake `gh` and clock: open, open, merged gives exit 0 after three reads; five failures in a row give exit 2; a run past `--for` gives exit 1.
- `test_cos_tick.py`: one table case each for a queued merge relay sent to a ticket with no `parentThreadId` (prints `merge-wait`) and a queued build relay (does not).
- `test_cos_route.py`: one table case, `approve-merge` to a ticket with no parent prints `merge-wait:`; the existing build-lane case shows it doesn't.
- `api.test.ts`: one table-driven case. A ticket in `merge` with `pr: 243` and a merged entry for the same id and `#243` is dropped, and its group goes with it when empty; the same id with merged `#200` stays; a second ticket in the same group keeps the group with `count` 1.

These fail without the fix: the tick and route cases print no line today, and today's `buildApi` keeps the row.

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` pass.

## Docs

- `chief-of-staff/SKILL.md`: description line, § Tools, § Tick (`merge-wait` row; the `send` row points to it), new § Merge wait, § Merged check mentions that the wait triggers it.
- `chief-of-staff/continuation.md`: the fallback in the merge lane starts the wait.
- `chief-of-staff/rotation.md`: take-over step 4 sub-step and the retired-thread row.
- `chief-of-staff/state-keys.md`: unchanged (no new keys).

## Non-goals

- How T3 sends run-finished notices.
- The other sweep checks, and the build lane's own "I may not hear" gap (the sweep's ready check covers it).
- Showing in the dashboard that a merge wait is running.

## Calls I made

- **Both fixes, not one.** The wait frees the slot; the filter is cheap and also hides the up-to-30-second gap the wait leaves, and the case where no wait started.
- **The wait polls GitHub every 30 seconds for up to 30 minutes, then gives up without restarting.** A merge child usually finishes in a few minutes; a run still open after 30 minutes is likely blocked, and the existing `say status` line covers it. At most 60 GitHub reads per wait.
- **The wake reuses the `notice:<child>` trigger** instead of adding a new trigger to `cos_tick.py`. The missing thing is exactly a finish notice, and that plan already handles a ticket that has left its stage.
- **The wait writes nothing.** It only wakes the thread; the sweep's merged check still does the branch check and the write.
- **Merge lane only.** The ticket names the merge slot; build has its own sweep coverage.
- **Take over starts a wait for every `merge` ticket under an older thread,** not only after a send. That is the case the ticket saw.
- **The rotation check stays the last tool call;** `t3_background_wait` goes right before it.
- **Dashboard match needs the ticket id and the PR number,** so a reopened ticket with a new PR still shows.
