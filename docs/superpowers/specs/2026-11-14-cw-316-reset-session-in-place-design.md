# CW-316: Reset the Chief of Staff session in place instead of rotating to a new thread

**Status:** Draft
**Ticket:** [#316](https://github.com/collective-wisdom-org/collective-wisdom/issues/316)
**Blocked by:** [CW-315](https://github.com/collective-wisdom-org/collective-wisdom/issues/315), the live test of T3 Code's fresh-context reset

## Goal

When the Chief of Staff's context gets too big, or its skill changes, it starts a fresh session inside its own thread instead of moving to a new thread. The thread ID never changes, so children started before the reset still deliver their finish notices to the Chief of Staff, and the handoff, failed-handoff and archiving machinery goes away.

## The CW-315 dependency

CW-315 is open and waiting on a manual run: T3 Code on this machine is 0.1.7, which has no `freshContext`, and the test needs a nightly from 2026-11-13 or later. Every part of this ticket rests on what that run finds.

- **Built now:** this spec, nothing else. No code, skill or doc change ships before CW-315's run record is on `main`.
- **Waits on CW-315:** the whole build. The build starts by reading the CW-315 run record in `docs/compatibility.md` § Runs on `origin/main`. With no record there, the build stops with `BLOCKED: waiting on the CW-315 run record` and changes nothing. A spec approval before CW-315 lands is fine; the build just waits.
- **What the record decides**, per harness (Claude Code, Codex, Cursor; Antigravity has no record and gets `none`):

| CW-315 result on that harness | Mode the harness gets |
|---|---|
| The self-send with `freshContext: true` works, the thread ID stays, the next call is new-thread size, and a child started before the reset delivers its finish notice to the new session | `reset` |
| As above, but a direct send is refused while children or a merge wait run, and a one-shot scheduled task with `freshSession` works | `reset`, sent through `schedule_task` instead of `t3_thread_send` |
| The reset fails any check above, and the queued `/compact` plus skill reload check passed | `compact` (the fallback) |
| Both fail, or the harness was not tested | `none` |

- **Hard stops in the build**, each `BLOCKED:` with the line from the record:
  - Claude Code gets `none`. Removing thread rotation would leave the team's main harness with no bound on context, so the user decides what happens next.
  - The record says `cos_user_check.py`, `cos_approve_pr.py` or another store-reading script fails on the upgraded schema. That is its own fix, and approvals must work before this ships.
  - The record says the Stop hook or `chiefSessionId` does not follow the new session. The hook is how a missed rotation check still fires.

## Today

Facts from `main` at `8ddace1`.

- `rotation.md` § Thread rotation: on `rotate:` the old thread sets `rotation`, launches a new thread with `t3_thread_launch` (`chief` modelSelection from `cos_models.py`), renames and unpins itself, retires itself with a `successor`, and ends with `Moved to ...`. The new thread runs take over steps 1 to 5. § Failed handoff covers a launch that never took over; `rotationHeldUntil` holds the next rotation 6 hours after one. Archiving and the Moved-to check exist to make this safe.
- `cos_rotation_check.py` `decide()` holds on `paused`, a non-null `rotation` and a future `rotationHeldUntil`; fires on size (220k, `SIZE_CAP`) or a skill change at a quiet turn. A turn is quiet with no `*-queued` ticket, `lastRelayAt` 10 or more minutes old, and the newest `retiredAt` 60 or more minutes old. `read_context()` reads only the Claude Code transcript (`agent_usage.py --context`), so Cursor has no size trigger and Codex has none at all.
- T3 Code's store (`~/.t3/userdata/statev2.sqlite`) on 0.1.7 has no context size: no column or payload in the runs, run attempts, provider sessions or session runtime tables mentions tokens or usage (checked on this machine on 2026-11-14).
- `cos_tick.py` prints `stop failed-handoff` (`rotation.from` is this thread and 10 minutes old) and `archive <thread>` lines (`archives()`); `cos_parent_check.py` prints `archive` and `keep` lines from a walk over `retiredThreads`.
- `cos_state.py`'s `retire` op takes an optional `successor`; `rotation` and `rotationHeldUntil` are top-level keys; `rotation-failed` is a sighting kind.
- Take over step 4 (the lean take-over pass) and step 5 work from the state file alone, and `resume` and resume mode reuse them.
- The Moved-to check is used by the handoff, take over step 1, the retired thread's successor fallback (entries without `successor`), the state rebuild (`startup.md` § State rebuild) and the relay chain walk (`ship-loop/reference.md`, which carries its own copy of the check).

## Design

### 1. Reset mode per harness

`cos_rotation_check.py` gets a `RESET_MODES` dict keyed by provider id (`providerInstanceId`, as `chiefProvider.provider` in state holds it), with values `reset`, `reset-scheduled`, `compact` or `none`. The build fills it from the CW-315 record per the table above; a provider missing from it is `none`. `docs/compatibility.md`'s "Stop hook (thread rotation)" row says the same per column, and the script's comment says to change both together.

The check reads `chiefProvider.provider` from state. A `rotate:` line gains the mode: `rotate: size 231k >= 220k; mode reset`. On a `none` harness it never prints `rotate:`; it prints `ok (no reset on <provider>; context=<N>k)` (or `size unknown`), which is where Codex is today.

### 2. The reset (modes `reset` and `reset-scheduled`)

On `rotate:`, in this order:

1. `top` op: `reset` = `{"id": <8 random hex chars>, "startedAt": now, "reason": <the rotate reason>}`. Save state.
2. Send the thread itself one message, `CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over.`: `t3_thread_send` to its own ID with `freshContext: true`, or for `reset-scheduled` a one-shot `schedule_task` on its own thread with `freshSession`, as the record describes it.
3. End the turn with one line: `Resetting my context (<reason>).` This is the last tool call's turn; nothing runs after the send.

If the send or schedule call errors, `top` op `reset` to `null`, write a `rotation-failed` sighting with the error, add one Cleanup line `Reset refused: <error>. Carrying on; the next rotation check tries again.` and finish the turn normally. The next turn's rotation check fires again because nothing changed.

### 3. Mode `compact`

Same marker (with `"mode": "compact"`), then two queued self-sends without `freshContext`: `/compact`, then the same `CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over.` The take over invokes the skill again, which reloads its full text. If the record's working procedure differs (another order, another command), the build follows the record and says so under Differs from spec. Failure handling is as in § 2.

### 4. Take over after a reset

`take over` keeps its name and becomes:

1. Load the skill, run `cos_rotation_check.py --skill-commit`, read state with `cos_state.py show`.
2. If the message that woke this turn is `CHIEF OF STAFF RESET <id>` and `reset.id` in state is that id: `top` op `reset` to `null` and `lastResetAt` to now. If the id does not match, or `reset` is null, the message is not ours: reply `Reset message not recognised; ignoring it.` and stop. A `take over` the user types, with no reset message, runs as `resume` (kill-switch.md § Resume).
3. Today's step 4, the lean take-over pass, unchanged.
4. Today's step 5 with `--record-takeover`, unchanged, ending with `Take-over done. <N> tickets in flight. Take-over context <K>k.` and its additions.

Steps 1 to 3 of today's take over (launch-message and Moved-to checks, the wake delete, pinning and the "Taking over from" line) go. The wake stays valid because it is bound to the same thread. `chiefSessionId` moves to the new session through the plain-mode save the check already does.

### 5. Holds and the quiet rule

`decide()` holds on `paused` and on a `reset` marker younger than 10 minutes (`ok (held: reset)`). A marker 10 or more minutes old no longer holds: the check fires again (`rotate: ...; reset never confirmed`), and the next take over clears it. The quiet rule's third clause reads `lastResetAt` instead of `retiredThreads`: `ok (skill change waits: reset <N>m ago)` within 60 minutes. A skill change is the same reset at a quiet turn. The `rotation` and `rotationHeldUntil` holds go; a leftover `rotation` in an old state file is ignored and `cos_state.py` drops it on the next `apply` that touches top-level keys.

### 6. Context size from T3's store

`read_context()` tries T3's store first, read-only, for the Chief of Staff thread (`chiefThreadId`), where the upgraded store keeps a context size; the transcript read stays as the fallback. If the store has no such field on the version CW-315 ran, this section is left out, the PR says so under Differs from spec, and Codex keeps having no size trigger. The store path and `mode=ro` URI follow `cos_idle_check.py --store`. A missing database, a missing row, an unexpected schema or a non-integer value all fall back to the transcript; only when both fail does the check exit 2 as today.

One table in `test_cos_rotation_check.py`: store has a size (used), store missing, row missing, schema changed, value not an integer (each falls back to the transcript), and both unreadable (exit 2).

### 7. Removals

- `rotation.md`: the handoff steps, take over steps 1 to 3, § Failed handoff, archiving, and the in-flight `rotation` paragraph. What stays: § Thread rotation (the check, triggers, quiet rule, the exit-2 item-count fallback, the size-trigger-off rule), the reset of § 2 and § 3, the new take over, § Resume mode and § Retired thread.
- `cos_tick.py`: `stop failed-handoff`, `archives()` and the `archive` lines.
- `cos_parent_check.py`: the archive walk and its `archive` and `keep` lines; it keeps the `full` and `idle` lines and the summary line.
- `cos_state.py`: `rotation` and `rotationHeldUntil` as known keys, the `rotation`-in-flight checks, and `successor` on `retire` (existing entries keep theirs; the `show` output still prints them). New keys: `reset` and `lastResetAt`.
- `models.md` and `cos_models.py`: the rotation successor rows and mentions. The `chief` role stays: startup.md step 3 still compares the thread's model with it.
- SKILL.md: the `stop failed-handoff` intro line and plan row, the `archive <thread>` plan row, and the pointers to removed sections. `state-keys.md`: the removed and new keys.
- Tests: the handoff, failed-handoff, archive and `rotationHeldUntil` cases in `test_cos_rotation_check.py`, `test_cos.py`, `test_cos_tick.py` and `test_cos_parent_check.py`. New cases go into the existing tables: the reset hold and its staleness, `lastResetAt` in the quiet rule, and the mode suffix (one row per mode).

### 8. Kept

The size and skill triggers, the quiet-turn rule, the Stop hook, `--record-takeover`, `takeoverContext`, `skillCommit`, `stop retired`, § Retired thread forwarding for threads retired before this ships, the relay chain walk, continuation children, `cos_handoff.py`, `cos_worktree_check.py`, `cos_merge_wait.py`, and the 220k cap.

### 9. Docs

- `docs/compatibility.md`: the "Stop hook (thread rotation)" row becomes "Context reset (rotation check)", one cell per harness from the record, with its notes and the gaps G7 and G8 updated.
- `agent-team/docs/agents/chief-of-staff.md`: the rotation line says it resets its session in place, and the "retired threads with no tickets are archived" line goes.

## Calls I made

- **Nothing is built before CW-315 lands.** Every part depends on the run: the reset itself, the fallback, the store field and the upgraded schema. A build started early stops at once with `BLOCKED: waiting on the CW-315 run record`.
- **Claude Code with no working reset or fallback stops the build.** The ticket says a failing harness gets the fallback, not thread rotation; if the fallback failed too, removing rotation would leave the main harness unbounded, so that is the user's call, not mine.
- **An untested harness gets no reset at all (`none`), not thread rotation.** For Cursor this drops today's skill-change rotation; for Codex nothing changes. Antigravity has no Chief of Staff today.
- **The Moved-to check is not removed outright.** The ticket lists it for removal, but the retired-thread successor fallback, the state rebuild and the relay chain walk, all kept, still use it. It leaves the handoff and take over and stays where those three use it.
- **The reset message carries a random id that must match the state marker.** The fresh session's first message is an agent message, so the id is what tells a real reset from a stray or injected one. A mismatch does nothing.
- **A user-typed `take over` runs as `resume`.** There is no new thread to take over any more.
- **A marker older than 10 minutes stops holding and the reset fires again.** That is the "tried again at the next check" path for a send that was accepted but never started a session.
- **A refused reset reuses the `rotation-failed` sighting kind** rather than adding a new one.
- **`lastResetAt` replaces `retiredAt` in the quiet rule**, with the same 60 minutes.
- **The store size read is dropped if the upgraded store has no size field**, and Codex keeps no size trigger. Today's 0.1.7 store has none.
- **The compatibility row is renamed** to "Context reset (rotation check)", since no thread rotates any more.
