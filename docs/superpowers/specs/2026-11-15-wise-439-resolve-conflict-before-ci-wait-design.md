# WISE-439: Resolve a conflict instead of waiting for CI that cannot start

**Status:** Shipped
**Ticket:** [#439](https://github.com/collective-wisdom-org/collective-wisdom/issues/439)
**Shipped:** in PR #454, with differences: [as-built](../as-built/2026-11-15-wise-439-resolve-conflict-before-ci-wait-as-built.md)

## Goal

A PR that conflicts with the merge target branch gets no CI: GitHub does not run `pull_request` workflows on it. Today the child waits about 10 minutes on checks that never come and then stops with a bare `no checks`, and the Chief of Staff can't tell that ticket from one still building. After this ticket, the CI wait sees the conflict within one poll and tells the child to resolve it, and the Chief of Staff's sweep flags a `build` ticket whose PR conflicts and has no checks, and sends the child the existing conflict relay.

## Today

Facts from main at `3157d1e`.

- `agent-team/scripts/wait-for-ci.sh` polls `gh pr checks` 20 times at 15 s when CI is declared (2 times when `project.md` declares none). It never reads `mergeable` or `mergeStateStatus`. With no checks it prints `wait-for-ci: no checks on PR #N at <sha>` and exits 2.
- `ship-loop/SKILL.md` § CI waits: exit 2 means run it again once; a second exit 2 is `BLOCKED:`.
- `open-pr/SKILL.md` § Primary loop step 1 reads `mergeable,mergeStateStatus` and merges `origin/<target>` on a conflict, but only at the start of the loop and after a push (step 4). A conflict that appears while the child waits is not seen.
- `open-pr/SKILL.md` § Conflict resolution starts on the Chief of Staff relay `CHIEF OF STAFF: the PR conflicts with <target>. Resolve it per open-pr § Conflict resolution and report MERGE READY.` (`CONFLICT` in `cos_head_check.py`), sent only after `MERGE READY` or an approval.
- `cos_ready_check.py` (run by `cos_sweep.py` on every tick) lists open PRs with `number,headRefName,headRefOid,comments` (plus `statusCheckRollup` in `ci` review mode) and prints `ready`, `building` or `no-pr` for each `build` ticket. It never reads `mergeable`. `gh pr list --json mergeable,mergeStateStatus` works (checked on PR #437: `CONFLICTING`, `DIRTY`).
- `cos_state.py` keeps a fixed set of ticket fields (`TICKET`); `changesRelayed` is the existing precedent for "relayed once for this head".

## Design

### 1. `wait-for-ci.sh`: a conflict line

- In the poll loop, on each try that finds no check rows, read `~/.collective-wisdom/scripts/gh.sh pr view <N> --json mergeable,mergeStateStatus`. If `mergeable` is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, stop at once and print `wait-for-ci: PR #N at <sha>: conflict with <target>` and exit **3**. `<target>` comes from `project_config.py` (a new `target` subcommand that prints `project_config.target_branch()`).
- `UNKNOWN` (GitHub has not computed it yet) or any other value keeps polling. A failed read of the two fields is not a conflict and keeps polling; it never turns into exit 3.
- This runs in a repo that declares no CI too, before the `no CI declared` exit 0: a conflicting PR can't merge either way.
- The `no checks` line gains the PR state: `wait-for-ci: no checks on PR #N at <sha> (mergeable <M>, mergeStateStatus <S>)`, with the values from the last read (`unknown` when it failed). Exit 2 as today.
- The usage comment at the top lists exit 3.

### 2. `ship-loop` § CI waits

- `conflict with <target>` (exit 3): the PR conflicts, so CI will not start. Merge `origin/<target>` into the branch, resolve what has one clear answer, run the Test command, push, and wait again. `BLOCKED: <question>` for anything unclear. Before the first `MERGE READY` this is `open-pr` § Primary loop step 1; in an `open-pr` § Conflict resolution run it is that section's step 1 again.
- A third `conflict with` line in one run (the target keeps moving under you) is `BLOCKED:` with the line.
- Time limit decision: no new cap. The two runs of `wait-for-ci.sh` (about 10 minutes of polling) stay the cap for "no checks". At the cap, stop with `BLOCKED:` and the second run's `no checks` line, which now names the PR's `mergeable` and `mergeStateStatus`.

### 3. `open-pr`

- § Primary loop step 2 points at the conflict line: on `conflict with <target>`, go back to step 1.
- § Conflict resolution gets one sentence at the top: a child that gets the `the PR conflicts with <target>` relay before its first `MERGE READY` treats it as Primary loop step 1 (merge, resolve, push, go on with the loop) and posts no `reviews stand` note. Nothing else in that section changes.

### 4. Chief of Staff: the ready check flags it

- `cos_ready_check.py` adds `mergeable,mergeStateStatus,statusCheckRollup` to its one `pr list` call (the rollup was only read in `ci` mode).
- For a `build` ticket with a matched PR, before the `ready` / `building` test: if `mergeable` is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, and the rollup is empty, print `conflict <PREFIX>-N #PR head <short sha>` and flag the ticket with reason `conflict`. Exception: when the ticket's state field `conflictHead` equals the PR's full head, the relay already went out for this head, so print `building <PREFIX>-N #PR (conflict relayed)` and flag nothing.
- A `MERGEABLE` PR with no checks yet, an `UNKNOWN` one, and a conflicting PR whose rollup has checks print what they print today.
- `cos_sweep.py`: `conflict` joins the ready part's action words, so the ticket goes on the `read in full:` list as `<PREFIX>-N (conflict)`.
- `cos_state.py`: new ticket field `conflictHead`, a full 40-hex SHA or null, set in any stage, like `changesRelayed`.

### 5. Chief of Staff prose

- `chief-of-staff/sweep.md` § Sweep: one bullet for the ready check's `conflict` line: the ticket gets the full read; § Child path does the rest.
- `chief-of-staff/SKILL.md` § Child path: a **Conflict** step after **Marker** and before **Stuck check**, only for a ticket the sweep listed with `conflict`, still in `build`, with no new marker. If the child's run is `running`, nothing (its own CI wait now sees the conflict). Otherwise send the child `CHIEF OF STAFF: the PR conflicts with <target>. Resolve it per open-pr § Conflict resolution and report MERGE READY.` (the `CONFLICT` text from `cos_head_check.py`, `<target>` the merge target branch) at once with `t3_thread_send`: the child keeps its build slot, so no slot check, queue or `cos_route.py`, as for the stuck-check restart. Then apply a `set` op with `conflictHead` set to the PR's full head, start the run wait (sweep.md § Run wait), add a Moving line `<PREFIX>-N: <short title>, PR conflicts with <target>, sent back to resolve it`, and skip the stuck check for that ticket this turn.

### Tests

- `test_wait_for_ci.py`: one table-driven test (extend the existing stub with `MERGEABLE` and `MERGE_STATE` values for the `mergeable,mergeStateStatus` query): no checks plus `CONFLICTING` ends with the conflict line and exit 3 without polling 20 times (count `sleep` calls); no checks plus `MERGEABLE` keeps today's poll and the `no checks` line with the state in it; no checks plus `UNKNOWN` polls on; checks present plus `CONFLICTING` watches as today; no CI declared plus `CONFLICTING` gives the conflict line.
- `test_cos_ready_check.py`: one table-driven test: a `build` ticket with a `CONFLICTING` PR and an empty rollup is flagged `conflict`; `DIRTY` alone is flagged; `MERGEABLE` with no checks is not; `CONFLICTING` with checks is not; `CONFLICTING` with `conflictHead` equal to the head is not.
- `test_cos_state.py`: `conflictHead` accepts a full SHA and null and rejects anything else, added to the existing field-validation table if there is one.

## Leaves out

- The Stop hook for a child that finishes mid-turn (WISE-435).
- § Conflict resolution after `MERGE READY` and the `Review after conflict resolution` setting (WISE-138, WISE-206).
- PR #437 itself.
- A conflict that appears while checks already ran on the head: the checks finish, and the existing paths (step 1 after the next push, `conflict: yes` in the approval request) catch it.
- The idle check, `cos_run_wait.py` and `cos_brief.py`: unchanged.

## Calls I made

- The Chief of Staff check lives in `cos_ready_check.py`, not the idle check or a new sweep part: it already lists the build lane's open PRs in one call, so the conflict costs two more JSON fields and no extra GitHub call.
- The Chief of Staff reuses the existing `CONFLICT` relay text word for word, which names `open-pr` § Conflict resolution. Rather than add a new relay kind, § Conflict resolution gets one sentence saying a child that hasn't reported `MERGE READY` yet treats it as Primary loop step 1.
- The relay goes to a build child only when its run is not `running`, once per PR head (`conflictHead` in state). A running child finds the conflict itself within one 15 s poll.
- The conflict relay to a build child skips `cos_route.py` and the slot check, like the stuck-check restart, because the child already holds its build slot.
- Exit code 3 for the conflict line, so `ship-loop`'s "exit 2 means run again" rule doesn't swallow it.
- `CONFLICTING` or `DIRTY` count as a conflict (either alone); `UNKNOWN` does not, since GitHub computes mergeability lazily and a later poll sees the real value.
- No new time cap: the existing two runs of the CI wait (about 10 minutes) stay the cap, and the `no checks` line now carries the PR state for the `BLOCKED:` line.
- A third conflict line in one run is `BLOCKED:`, so a target branch that keeps moving can't loop a child forever.
- The ready check flags a conflict only with an empty rollup, as the ticket says. A conflicting PR whose checks already ran is left to the existing paths.
- `project_config.py` gets a `target` subcommand so the shell script reads the merge target branch the same way the Python scripts do.
