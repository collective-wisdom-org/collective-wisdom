# CW-315: Test the T3 Code fresh-context reset on the Chief of Staff thread

**Status:** Shipped
**Shipped:** in PR #330, with differences: [as-built](../as-built/2026-11-14-cw-315-fresh-context-reset-test-as-built.md)
**Ticket:** [#315](https://github.com/collective-wisdom-org/collective-wisdom/issues/315)
**Related:** CW-53 (the compaction test it deferred), `chief-of-staff/rotation.md` § Thread rotation

## Prerequisite: T3 Code upgrade

This ticket cannot be built on this machine today. `t3_environment_read` reports `serverVersion` `0.1.7` (read 2026-11-14). The run needs a nightly built on 2026-11-13 or later, or the first stable release after v0.1.9:

- 0.1.7 has no `freshContext` on `t3_thread_send` and no `freshSession` on scheduled tasks.
- 0.1.8 and 0.1.9 have both, but send delegated-task notices to the old session after a scheduled fresh run (`pingdotgg/t3code` issue 36087). The fix, PR 36103, merged 2026-11-13 and ships in nightlies only so far. Check 2 below would fail on those versions for a reason that is already fixed.

The build starts by reading `serverVersion`. If it is 0.1.9 or lower and not a nightly from 2026-11-13 or later, the build stops with `BLOCKED: T3 Code is <version>; CW-315 needs a nightly from 2026-11-13 or later, or the first stable after v0.1.9`. The user upgrades T3 Code; a ship-loop child cannot.

Which checks need the upgrade:

| Check | Needs the upgrade |
|---|---|
| 1. Self-send with `freshContext` | yes |
| 2. Notice from a child started before the reset | yes (and the 36103 fix) |
| 3. Reset with children running and during a merge wait | yes |
| 4. User-message scripts and store readers | yes: the point is the upgraded store schema |
| 5. Stop hook and `chiefSessionId` | yes: there is no reset to follow without it |
| 6. Queued `/compact` fallback | no: `t3_thread_send` and `/compact` exist on 0.1.7 |
| 7. Checks 1 to 3 on Codex and Cursor | yes |

Check 6 can run before the upgrade. It is still recorded in the same run entry, so the record has one T3 Code version per check.

## Goal

One recorded run shows, per harness, whether the Chief of Staff thread can reset its own provider session with `freshContext: true` and keep working: same thread ID, small context, children's notices arriving, scripts and the Stop hook following the new session. `docs/compatibility.md` gets a dated run record with a pass or fail per check. Nothing else ships.

## Today

Facts from `main` at `baa748a`.

- Rotation launches a new thread and hands off (`rotation.md` § Thread rotation). T3 sends a child's finish notice only to its `parentThreadId`, so each rotation leaves children under a retired thread, and archiving waits on them.
- `cos_rotation_check.py` saves `chiefSessionId` on each plain run when it differs from `$CLAUDE_CODE_SESSION_ID` (Cursor: the conversation id). The Stop hook acts only when the Stop payload's `session_id` equals `chiefSessionId`.
- Scripts that read T3's store open `~/.t3/userdata/statev2.sqlite` read only:
  - `cos_user_check.py` (and `cos_approve_pr.py`, which uses it): `orchestration_v2_projection_messages`.
  - `cos_peer.py`: `orchestration_v2_projection_messages`, `orchestration_v2_projection_threads`.
  - `cos_child_read.py`, `cos_idle_check.py`: `orchestration_v2_projection_runs`, `orchestration_v2_projection_threads`, `orchestration_v2_projection_turn_items`, `orchestration_v2_turn_item_positions`.
- A Chief of Staff on Codex starts no children until a routing table exists (CW-280, G2). A Cursor Chief of Staff has run once (2026-11-09).
- The compatibility doc's [Recording a run](../../compatibility.md#recording-a-run) steps run in a throwaway private repo, because a second Chief of Staff in collective-wisdom would fight the live one over `.agent-team/state.json`.

## Design

Docs only. The build edits `docs/compatibility.md` and this spec's closeout lines.

### Who does what

A ship-loop child may not call `t3_thread_send`, `t3_thread_launch` or `schedule_task`, and cannot start a thread on another harness. So the run happens in a scratch Chief of Staff thread the user starts, and that thread makes the sends to itself. The build child then reads the scratch threads (`t3_thread_read`, `t3_thread_list`), the scratch repo's state (`cos_state.py show` from its root checkout) and the scratch store, and writes the record.

So the build runs in two stops:

1. Version check, then `BLOCKED: run the CW-315 run sheet` with the run sheet below and a request for the scratch thread IDs, one per harness.
2. After the Chief of Staff relays the thread IDs, read them and write the record.

### Scratch setup

Per [Recording a run](../../compatibility.md#recording-a-run) steps 1 to 3: a new private repo with four one-line tickets (README lines), set up with `set up this repo`. Harnesses run one after another on the same repo, never two at once: before the next harness, the user sends `stop everything` to the last scratch Chief of Staff, starts the next harness's thread and sends `take over`.

### Run sheet

Each step names the message the user sends to the scratch Chief of Staff thread and what the build reads to grade it. "The reset" means the thread sends itself `take over` with `t3_thread_send` and `freshContext: true`. `take over` is the message a reset session needs anyway: the take-over pass rebuilds the working set from state.

1. **Self-send.** With no children running, the user asks the thread to do the reset. Grade:
   - Pass when `t3_thread_list` shows no new thread, `t3_thread_read` on the same thread ID shows the `take over` run, and that run's session ID differs from the one before.
   - "The size of a new thread": the context size of the reset's first turn (`agent_usage.py --context`, which reads the running session, so the scratch thread runs it at the end of that turn and the build quotes its line) is within 25% of the first take-over turn of a thread started fresh on the same repo and state. The build records both numbers. On Cursor, where there is no context size (G8), record `size unknown` and grade the rest.
2. **Child notice across the reset.** `start the team` with one ticket in Todo, wait until its spec child is running, then the reset. Pass when the child's finish notice (`BUILD READY`) runs in the new session of the same thread and the Chief of Staff relays it. Fail if it lands in the old session, nowhere, or only after a user nudge.
3. **Reset under load.** Two cases, each followed by the reset:
   - Two children running (approve the first spec, start a second ticket).
   - A merge wait running (`approve <N>` on a `MERGE READY`, while `cos_merge_wait.py` waits on CI under `t3_background_wait`).
   Pass when the send is accepted and the children's notices and the merge wait's wake reach the new session. If T3 refuses the direct send, the thread instead schedules a one-shot task that sends `take over` with `freshSession`, and the run records `direct: refused; scheduled: <pass or fail>`.
4. **Scripts after the reset.** In the new session:
   - Send `status` and `approve <N>` for an item the user approved before the reset (or re-check one): `cos_user_check.py latest` and `cos_approve_pr.py <PREFIX>-N` must find the pre-reset user message.
   - Run `cos_peer.py`, `cos_child_read.py` and `cos_idle_check.py` as the tick does. Pass when none exits 2 (`cannot read`).
   - The build also dumps the schema of the tables listed under Today from the upgraded store (`sqlite3 -readonly ~/.t3/userdata/statev2.sqlite '.schema <table>'`) and records any table or column the scripts use that is gone or renamed. This is a read of the user's own store, read only.
5. **Stop hook and `chiefSessionId`.** After the reset's first turn, `cos_state.py get chiefSessionId` must equal the new session's ID. Then, on a quiet turn, the user sets a stale `skillCommit` in scratch state (`cos_state.py apply`), and the hook must answer `rotate:` for the new session. Pass on both. If only the first shows, record `partial: hook not seen`.
6. **`/compact` fallback.** The thread sends itself a queued `/compact` (no `freshContext`). Pass when the transcript shows a compaction (the next turn's context is smaller and the transcript has a compact boundary) and invoking `chief-of-staff` afterwards returns the full `SKILL.md` text (its last section is present, not a summary). Runs on Claude Code only; it can run before the upgrade.
7. **Codex and Cursor.** Repeat checks 1 to 3 in a Codex Chief of Staff thread and a Cursor one, where each can be started. A Codex Chief of Staff starts no children while there is no routing table (G2), so on Codex checks 2 and 3 record `not run: no children on Codex (CW-280)` unless that has changed by the run.

### The record in `docs/compatibility.md`

- **A run entry** under [Runs](../../compatibility.md#runs), newest first, titled `### <date>, fresh-context reset (CW-315)`: T3 Code version and whether it is a nightly, scratch repo, thread IDs per harness, then one line per check per harness: `pass`, `fail: <what happened>`, `partial: <what>`, or `not run: <why>`, each with the quoted tool output or reply it rests on. The two context sizes from check 1 and the schema diff from check 4 go in it.
- **A Matrix 1 row**, `Fresh-context reset (T3 Code after 0.1.9)`, after the `Stop hook (thread rotation)` row, one cell per harness from the run: `works` only where checks 1 to 3 all passed, `partial` naming the failed check, `untested` where it did not run. Antigravity is `untested` with a gap.
- **Gaps.** Each failed or partial check gets a gap line, `Ticket: none yet`. The child does not file tickets; `MERGE READY` lists them under "Left open" for the Chief of Staff.
- **Last checked** line: dated the build day, naming CW-315.

## Leaves out

- Changing rotation, the rotation check, the Stop hook or state keys. That is the follow-up ticket, and only for a harness that passed.
- Upgrading T3 Code. The user does it.
- Starting the scratch threads or making the sends: the user and the scratch Chief of Staff do that.
- Filing tickets for failures.
- Antigravity: no Chief of Staff can run there yet (G17, G18).
- Re-running the CW-53 size-cap question. Check 6 records whether compaction works; whether to raise the 220k cap stays with that follow-up.

## Calls I made (surprising first)

- **The reset message is `take over`**, not a custom prompt. A reset session has no context, and the take-over pass is the existing way to rebuild it from state, so the run tests the path a real rotation would use.
- **The build stops twice**: once to block on the version, then to wait for the user's run. A child cannot send to threads or start them, so it can only grade a run someone else drives.
- **"The size of a new thread" means within 25% of a freshly started thread's first take-over turn** on the same repo and state. The ticket gives no number; 25% leaves room for state that changed between the two turns.
- **A matrix row is added**, though the ticket asks only for a run record: a run with no cell leaves the matrix behind the record, and the `Keeping it current` rule says cells rest on runs.
- **One scratch repo, harnesses in turn**, handed over with `stop everything` and `take over`, instead of one repo per harness: fewer setups, and two Chiefs of Staff never share state at once.
- **Check 6 may run before the upgrade**, since it needs nothing new from T3 Code. It is the fallback if the reset fails, so knowing early is useful.
- **0.1.8 and 0.1.9 are refused** at the version check even though they have `freshContext`, because check 2 would fail there on the known notice bug.
- **The schema check reads the user's live store** read only, the same way the scripts do. It records column changes; it does not fix any script (no script change ships).
- **Failures become gap lines, not tickets**, because a child changes only its own ticket.
- **Check 5 forces the hook with a stale `skillCommit`** in scratch state, the cheapest trigger that does not need a 220k context.

## Acceptance

- `docs/compatibility.md` has the dated run entry with the T3 Code version and a pass, fail, partial or not-run line for each check per harness, each resting on a quoted read.
- Matrix 1 has the `Fresh-context reset` row filled from that run, and each cell that is not `works` names a gap.
- No skill, script, test, hook or state change is in the PR.
