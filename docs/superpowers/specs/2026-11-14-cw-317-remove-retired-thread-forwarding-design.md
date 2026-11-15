# CW-317: Remove retired-thread forwarding

**Status:** Draft
**Ticket:** [#317](https://github.com/collective-wisdom-org/collective-wisdom/issues/317)
**Follows:** [CW-316](2026-11-14-cw-316-reset-session-in-place-design.md), the in-place reset (PR #333)

## Goal

Since CW-316 the Chief of Staff resets its session inside its own thread, so its thread ID no longer changes and no thread retires. The code that forwards notices from retired threads, walks the chain of retired threads, and keeps `retiredThreads` in state now only serves children started before CW-316. When none of those children is left, remove it.

## Precondition

The live state at the time of writing (`.agent-team/state.json` in the root checkout, read only) has eight `retiredThreads` entries, all archived, and one ticket (CW-317 itself) whose `parentThreadId` is the current Chief of Staff thread. No ticket has a `parentThreadId` in `retiredThreads`. The PR runs this check again just before it is marked ready and pastes the output under `## Proof`:

```bash
python3 -c "import json; s=json.load(open('.agent-team/state.json')); r={x.get('threadId') for x in s.get('retiredThreads', [])}; bad=[k for k,t in s['tickets'].items() if t.get('parentThreadId') in r]; print('retired:', len(r), 'tickets:', len(s['tickets']), 'under a retired parent:', bad or 'none')"
```

If that list is not empty when the PR is ready, the build stops with `BLOCKED:` instead of reporting `MERGE READY`.

## What changes

### Skills and role docs (`agent-team/.claude/skills/`)

- **`chief-of-staff/rotation.md`**
  - Remove § Thread rotation: Retired thread (the forwarding table and the successor rules).
  - Remove the **Moved-to check** paragraph and the paragraph after it. After this ticket nothing uses the check: its three users were the successor fallback, the state rebuild and the children's chain walk, and all three go.
  - Remove "A retired thread never runs it" from § Thread rotation, and "a retired thread" from the opening line.
  - § Thread rotation: Resume mode: drop the `unretire` op and the retired-thread reply. When `chiefThreadId` names another thread, the reply is always `State names <id> as Chief of Staff; not resuming. Check .agent-team/state.json.`
- **`chief-of-staff/SKILL.md`**: the tick's `stop retired` line becomes `stop not-chief`. It means "state names another thread as Chief of Staff". The turn does nothing but reply `State names <id> as Chief of Staff; this thread is not it. Check .agent-team/state.json.`, and only when the user wrote. A notice or agent message gets no reply. The skip rules (run-started notice, project manager run-finished notice, `start the team` when state names this thread or none) stay as they are. Remove the forwarded-notice clause from the `notice:<thread>` row and the Moved-to check from the list of thread reads.
- **`chief-of-staff/startup.md`** § State rebuild: keep only threads whose `parentThreadId` is this thread. Remove the Moved-to check on this thread, the `CHIEF OF STAFF ROTATION from <id>` chain rebuild, and the `retire` op from the list of ops the rebuild writes. Tickets whose child sits under another thread are still found from the tracker and go to continuation children as today.
- **`chief-of-staff/ticket-helper.md`** § Helper test: `<id>` must be this thread. Remove the bullet about helpers started by a retired thread.
- **`chief-of-staff/state-keys.md`**: remove `retiredThreads` from the example and the key list.
- **`chief-of-staff/continuation.md`** and **`report-format.md`**: the Moving line reads `<PREFIX>-N moved to a new child (old one under an older thread)`, the same words `cos_parent_check.py` uses.
- **`ship-loop/SKILL.md`** § Approvals: a spec approval's `Approval in thread:` must be the Chief of Staff thread in the task. Any other thread is `BLOCKED: approval thread <id> is not the Chief of Staff thread in my task`. Remove the pointer to the chain walk and the sentence about the rotation launch message. § Continuation tasks drops "and the `Approval in thread:` chain check" for the same reason.
- **`ship-loop/reference.md`**: remove § Relay chain walk.

### Scripts (`agent-team/scripts/`)

- **`cos_state.py`**: remove the `retire`, `archive` and `unretire` ops and their helper, the `retiredThreads` default in `apply_ops`, its prune rule, and the `retired:` line of `show`. Remove `retiredThreads` from `TOP`, so `prune` drops a leftover key as it drops any unknown top-level key, and `show` lists it under `unknown keys` until then. Update the docstring.
- **`cos_tick.py`**: `stops()` returns `stop not-chief` when `chiefThreadId` is set and is not this thread; it no longer reads `retiredThreads`. `check_state` stops checking retired thread ids.
- **`cos_peer.py`**: a sender is the Chief of Staff only when it is its project's `chiefThreadId`. Remove the `retiredThreads` read and its `Unreadable` case, and fix the docstring.
- Tests: update `test_cos.py`, `test_cos_tick.py`, `test_cos_peer.py` and `test_cos_rank.py` to match. Drop the retire, archive and unretire cases and the `retiredThreads` bad-state cases. Keep one row in the existing `stops()` table showing that a leftover `retiredThreads` entry for this thread no longer stops the tick, and one row in the `cos_peer` table showing that a thread that is not `chiefThreadId` is refused.

### Docs

- **`docs/compatibility.md`** G26 (a merge wait across a reset with a retired parent): mark it retired. It needs a ticket under a retired Chief of Staff thread, and those can no longer exist.

## What stays, and why

The ticket asks the PR to decide these and keep them. All four stay, because each serves a case that has nothing to do with retired threads:

| Kept | Still needed for |
|---|---|
| Continuation children (`continuation.md`, `TEAM MODE. CONTINUE`) | `adopt N` on a ticket started by another thread, and tickets found by a state rebuild or a resume in a new thread, whose old child sits under a thread that is no longer `chiefThreadId` |
| `cos_handoff.py` | Builds the `HANDOFF` block for those continuation tasks |
| `cos_worktree_check.py` | Decides whether a relay can still go to the old child or needs a continuation child |
| `cos_merge_wait.py` | Merge waits for any ticket, including an adopted one in the merge lane |
| `cos_parent_check.py` | The take-over sweep's "still under an older thread" count, which the same cases still produce |

The PR description repeats this table.

## Leaves out

- Removing continuation code (out of scope per the ticket).
- Removing the `Approval in thread:` line from spec relays. `cos_user_check.py` still reads it to find the user's message, so it stays even though it now always names the Chief of Staff thread.
- Cleaning the live state file. The next `prune` drops `retiredThreads`; nothing writes the root checkout's state in this ticket.
- Old spec, plan and as-built docs under `docs/superpowers/`. They are history.

## Acceptance

- The precondition check shows no ticket under a retired parent, pasted in the PR.
- `adopt N`, the state rebuild and resume mode in a new thread still work: their sections still read correctly with the retired-thread clauses gone, and the continuation path is untouched.
- `python3 -I -m pytest -q agent-team/scripts` passes, including `test_section_pointers.py` and `test_call_sites.py`, with no reference left to § Thread rotation: Retired thread, § Relay chain walk, the Moved-to check, or the removed ops.
- `/usr/bin/grep -rnE "retiredThreads|Moved-to|Relay chain|unretire|stop retired" agent-team` finds nothing outside `docs/superpowers/`.

## Calls I made

- **The tick's `stop retired` line is renamed `stop not-chief`.** With no retired threads the old name would mislead. The condition it keeps (state names another thread) still needs a stop so two threads never act as Chief of Staff at once.
- **A non-chief thread replies only to the user, and never forwards.** Old retired threads are all archived, so nothing should wake them; if one is woken, it says which thread is Chief of Staff and does nothing else.
- **The Moved-to check goes entirely**, including the state rebuild's "am I retired?" test. A thread that rebuilds state now assumes it is the Chief of Staff, as it would on any first start.
- **A child now refuses a spec approval from any thread but the one in its task**, instead of walking a chain. A queued approval stored before a resume in a new thread would hit this; the user then approves again in the current thread. No such queued approval exists today.
- **`retiredThreads` leaves `TOP`**, so `prune` cleans it from state instead of the build editing the live state file.
- **`docs/compatibility.md` G26 is marked retired** rather than kept open, since its test setup can no longer occur.
