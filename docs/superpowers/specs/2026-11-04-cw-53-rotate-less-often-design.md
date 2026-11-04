# CW-53: Rotate the Chief of Staff thread less often

**Ticket:** [CW-53](https://github.com/dbeallor/collective-wisdom/issues/53)
**Status:** Draft

## Goal

The Chief of Staff thread rotates only when it buys something. On 2026-11-04 state showed eight retired threads in about two and a half hours, mostly from the skill-change trigger, which fires on every merged PR that touches the skill. Each take-over reloads the skill and lands around 119k context, so a rotation is expensive and should be rare.

## Non-goals

- Shrinking what a take-over loads (CW-23).
- Changing the handoff, take-over, retired-thread or failed-handoff steps.
- Changing the item-count fallback when the context is unreadable.
- Changing the 90k "Take-over ended at <N>k" Cleanup line or the `takeoverContext` size-trigger-off rule.
- Raising or removing the size cap. That waits for real take-over numbers and a long-thread compaction test (see Size cap).

## Design

### Triggers after this ticket

`decide()` in `agent-team/scripts/cos_rotation_check.py` applies, after the existing holds (`paused`, `rotation`, `rotationHeldUntil`):

| Trigger | Fires when |
|---|---|
| Skill change | the skill commit differs from `skillCommit` (on `main` only, as today) **and** the turn is quiet **and** the last rotation was an hour ago or more |
| Size | context is 220k or more (safety net; unchanged) |

The age trigger goes, with `AGE_HOURS` and `AGE_MIN_CONTEXT`.

### Quiet turn

The skill-change trigger waits unless all of these hold:

1. No ticket in state is in a `*-queued` stage.
2. No relay or child start in the last 10 minutes: top-level `lastRelayAt` is absent or 10 minutes old or more.
3. The newest `retiredAt` in `retiredThreads` is 60 minutes old or more (or there is none).

Rule 3 is both the hourly cap and the ticket's "no take-over in the last 30 minutes": a take-over follows its handoff within a minute or two, and handoff step 5 writes `retiredAt`, so an hour since the last `retiredAt` also means more than 30 minutes since the last take-over.

When the skill changed but the turn isn't quiet, the line is `ok (skill change waits: <reason>)`, where the reason is `queued <PREFIX>-N`, `relay 4m ago` or `rotated 23m ago` (the first that applies). The Stop hook treats it like any `ok` line. The next quiet turn rotates. If the size trigger also fires, size wins and rotates (it ignores quiet, as today).

### `lastRelayAt`

A new top-level state key. `cos_state.py` stamps it with now on:

- a `start` op that creates a ticket (a new child), and
- a `stage` op whose new stage is `spec`, `build` or `merge` (a relay sent, or a queued relay sent when a slot freed, or a continuation start).

The skill never sets it by hand, and a `top` op that sets it is rejected. `show` prints it with the rotation keys. `prune` leaves it. `state-keys.md` gets one bullet.

### Size cap

`SIZE_CAP` stays at 220k. Rotation exists to keep the per-turn working set small, and take-overs measure 80-110k, so 220k leaves room. Raising the cap would assume a context window nobody has verified, and the quiet-turn rule doesn't depend on it.

The ticket asks to raise the cap to where the harness compacts, or remove it once a long thread shows compaction keeps the working set. This ticket doesn't do that. It collects the numbers first: the `Take-over context` line below records each take-over's size in the thread. The cap goes up later, once a long thread has shown compaction keeps the working set. I'll note on CW-53 that the test wasn't run and that raising the cap is left for a follow-up; a child changes only its own ticket, so the Chief of Staff or the user files that one.

### Take-over context in the report line

`--record-takeover` already measures the context. Its printed line gets `; take-over context=<N>k` appended, and take-over step 5's post becomes:

`Chief of Staff moved here from <old thread link>. <N> tickets in flight. Take-over context <K>k.`

`<K>` comes from that line. The rest of step 5's additions stay as they are.

### Docs

- `agent-team/.claude/skills/chief-of-staff/rotation.md` § Thread rotation: the trigger table, the line that names the constants, the quiet-turn rule and the `skill change waits` line, take-over step 5's post.
- `agent-team/.claude/skills/chief-of-staff/state-keys.md`: the `lastRelayAt` bullet; the `skillCommit` bullet says the change waits for a quiet turn.
- `agent-team/docs/agents/chief-of-staff.md`: "on measured context size, age or a change to its own skill" loses "age" and says the skill change waits for a quiet turn.
- `SKILL.md` only where it names the age trigger, if anywhere.

### Tests

- `test_cos_rotation_check.py` `test_decide`: drop the age rows; add rows for a queued ticket, a relay 5 and 11 minutes ago, a rotation 30 and 61 minutes ago, and size beating a non-quiet skill change. One table, as today.
- `test_cos.py`: one table row each that `start` and a `stage` op into an active stage stamp `lastRelayAt`, and a move into `awaiting-spec` does not.
- One check that `--record-takeover` prints `take-over context=`; it fits as a column in the existing `test_plain_saves_session_and_takeover`.

## Calls I made

- **Size cap stays at 220k** (changed after review: the first draft raised it to 400k). The 400k number assumed a 1M window that wasn't verified, and the compaction point isn't measured. Raising it is left for later, gated on a long thread showing that compaction keeps the working set.
- **One hour since the last `retiredAt` covers both the hourly cap and the 30-minute take-over rule**, instead of a separate take-over timestamp.
- **"No relay sent in this turn" becomes "no relay or child start in the last 10 minutes"**, stamped by `cos_state.py`. The script can't see the turn, and the Stop hook can't be told, so it uses a time window. A new child start counts too, since it is the same kind of hand-off.
- **Quiet and the hourly cap apply only to the skill-change trigger.** The size trigger still rotates any time, since it is the safety net.
- **Rotation waits, it isn't skipped.** The skill commit stays different from `skillCommit`, so the first quiet turn rotates.
- The report line shows the take-over context in thousands (`Take-over context 119k`), matching the rest of the script's numbers.
