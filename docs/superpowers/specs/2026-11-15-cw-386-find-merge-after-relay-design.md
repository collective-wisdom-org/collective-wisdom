# CW-386: Find a merge soon after the Chief of Staff relays a merge approval

**Status:** Shipped
**Ticket:** [#386](https://github.com/collective-wisdom-org/collective-wisdom/issues/386)
**Shipped:** in PR #405, as specified

## Goal

After the Chief of Staff relays a merge approval to a child, it finds the merge within a minute or so, even when T3's finish notice for that child never arrives. Until it knows, it tells the user the PR's state from GitHub, not "merge in progress" from its own relay.

## Today

- `cos_route.py` (line 136) prints `merge-wait: <T>` for a merge-lane send only when the ticket has no `parentThreadId`. `cos_tick.py` (line 222) does the same for a queued merge it sends (`merge-wait <T>` plan line). A ticket whose parent is this thread gets no wait: the Chief of Staff trusts the finish notice.
- `SKILL.md` § Tick already says "A merge send adds a `merge-wait` line", with no parent condition. The scripts disagree with it.
- `sweep.md` § Merge wait runs `cos_merge_wait.py` in the background: it polls the PR every 30 seconds for 30 minutes and, on `merged` or `closed`, wakes the thread into a tick that runs the merged check. On `left merge` it does nothing. Two waits on one ticket are harmless.
- `status`, `where's` and a user question already run the tick, which runs the sweep and its merged check. The incident on 2026-11-15 (CW-348) had no turn at all for 5 minutes: nothing woke the thread.

## Design

### 1. Every merge send starts the merge wait

- `cos_route.py`: a merge-lane `route: send merge` prints `merge-wait: <T>` whatever the parent. The continuation path is unchanged (its `fallback:` line already says to start the wait when it falls back to the old child). The `moving:` line is unchanged: it still appears only when no parent is known, since a parent equal to this thread may still send its notice.
- `cos_tick.py`: a `send <T> merge` plan line is always followed by `merge-wait <T>`. Its docstring and the comment change to match.
- `cos_route.py` docstring: `merge-wait: <T>` is "a merge-lane send: start the merge wait".

When the finish notice does arrive, its tick removes the ticket from `merge`, and the wait ends on its next poll with `left merge`, which does nothing. When the notice is lost, the wait sees `MERGED` within 30 seconds and wakes the thread into the tick that runs the merged check, which frees the merge slot and starts the next queued merge.

### 2. Docs

- `sweep.md` § Merge wait: the opening sentence covers every merge send ("a finish notice can be lost even when this thread is the parent"), and the list of starts says `cos_route.py` and the tick print it for every merge send. The `still open` case drops "the Moving line already told the user to say status", since a send to a child of this thread has no Moving line; it still runs the tick once.
- `SKILL.md` § Tick `send` row: unchanged (it already says a merge send adds a `merge-wait` line).
- `status.md` § Status layout rules: a `Merging` row's Next comes from this turn's merged check: `PR #N open, merge sent <time>` while the PR is open, never "merge in progress" from the relay alone. A merged ticket has already left state and gets the `Merged:` line as today.

### 3. Tests

- `test_cos_route.py`, `test_the_merge_lane_starts_the_merge_wait`: the row `("approve-merge", "awaiting-merge", ME, ...)` flips to `wait=True`. This is the row the ticket asks for: a merge send with a parent equal to the chief thread.
- `test_cos_tick.py`: one act-plan row where a queued merge under this thread is sent and gets `merge-wait ABC-1`; the existing merge rows gain the line.

## Leaves out

- Running the merged check on turns that run no tick (ticket helper, team-change and cross-repo requests). Those turns don't answer about ticket progress, and the merge wait wakes the thread anyway.
- Changing how T3 sends finish notices, or any timer or scheduled wake (CW-16).
- Changing the merge wait's poll interval or 30-minute limit.
- Take over step 3.2, which already starts a wait for every `merge` ticket whose parent is not this thread (after a take over, that is every one).

## Calls I made

- Chose "start the merge wait for every merge relay" over "run the merged check on the next turn of any kind". The wait finds the merge with no user message, which the second option can't; and `status` and questions already run the merged check through the tick.
- The `moving:` line ("I may not hear when this run ends") stays only for a send with no known parent. A child of this thread usually does send its notice, so telling the user to say `status` every merge would be noise.
- One extra background `gh pr view` every 30 seconds while a merge runs, even when the notice arrives. The wait stops on its next poll after the ticket leaves `merge`, so the cost is a poll or two.
- The `Merging` row wording is `PR #N open, merge sent <time>`.

## Acceptance

- A merge relayed to a child under this thread, whose finish notice never arrives, leaves `merge` within about a minute of the PR merging, with no user message, and the next queued merge can start.
- `cos_route.py` has a test row for a merge send with a parent equal to the chief thread, and it prints `merge-wait:`.
- A `status` or question on a `merge` ticket answers from the merged check.
