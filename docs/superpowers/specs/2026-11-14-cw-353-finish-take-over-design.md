# CW-353: Finish the Chief of Staff take-over pass when a user message interrupts it

**Status:** Shipped
**Shipped:** in PR #368, as specified
**Ticket:** [#353](https://github.com/collective-wisdom-org/collective-wisdom/issues/353)

## Goal

A take-over pass that a user message interrupts still runs to the end: `reset` cleared, `skillCommit` set, the slot fill run and `Take-over done.` posted. The message gets its answer after the pass. If a turn ends with the pass unfinished, the same turn or the next one finishes it without the user asking.

## Today

Facts from main at `81c114b`.

- `agent-team/.claude/skills/chief-of-staff/rotation.md` § Thread rotation "Take over" has four steps. Step 2 checks the reset message and clears `reset`. Step 3 is the lean pass. Step 4 sets `skillCommit`, runs `cos_rotation_check.py --record-takeover` and posts `Take-over done.`
- Step 2 takes the reset message to be **the newest `user_message`** in the thread. A user message that lands during the take over becomes the newest one, so a rerun of step 2 would reply `Reset message not recognised; ignoring it.` and stop, leaving `reset` set.
- Nothing in state says a take over is in progress. `SKILL.md` § Turn start routes each message by its own kind, so a title refresh request (a message that is not a command) gets an answer and the pass is forgotten.
- `cos_rotation_check.py` prints `ok (held: reset)` while the `reset` marker is under 10 minutes old, with no context size. The Stop hook (`cos_rotation_check.py --hook`) blocks a turn's stop on any line that does not start with `ok`, once per stop.
- `cos_tick.py`'s look plan has no check for an unfinished take over.

## Design

One new state key marks the pass as running. Two existing checks act on it: the Stop hook catches a turn that ends mid-pass, and the tick catches the next turn. Step 2 finds the reset message even when newer messages sit above it.

### The `takeover` key

A new top-level state key: `null`, or `{"startedAt": <time with a zone, not in the future>, "mode": "take-over" | "resume"}`.

- Take-over step 1 sets it first, with mode `take-over`, before anything else in the pass.
- Resume mode (rotation.md § Thread rotation: Resume mode) sets it with mode `resume` at the same point.
- Step 4 clears it in the same `top` op that sets `skillCommit`, before the rotation check runs.
- Step 2 clears it when step 2 stops the take over: `Reset message not recognised; ignoring it.`, and a plain `take over` that goes to kill-switch.md § Resume or is ignored.

`cos_state.py` accepts it as a top key and rejects any other shape, the way it checks `reset`. `cos_state.py show` prints `takeover=<mode since time>` or `takeover=-`. `state-keys.md` documents it.

### Rotation check: `finish:`

In `cos_rotation_check.py` `decide()`, right after the `paused` hold: when `takeover` is a dict, the line is `finish: take over unfinished since <N>m; mode <take-over|resume>`. It comes before the `reset` hold, so a pass abandoned before step 2 is caught too.

- The line does not start with `ok`, so the Stop hook blocks the stop once, with its usual reason `<line>; run chief-of-staff/rotation.md § Thread rotation`. The turn goes back to the model and it finishes the pass in that same turn.
- The plain call prints the same line. Step 4 clears `takeover` before `--record-takeover`, so the final check of a finished pass never sees it and prints its context size as before.

### Tick: finish first

In `cos_tick.py`, every look plan except `start` checks `takeover` before the provider check. When it is set, the plan is the one line `follow rotation.md § Thread rotation: Finish take over`. The act plan (`--after-reads`) does not check it, because take-over step 3.4 calls the act plan from inside the pass. `start` is left out because "start the team" with tickets in state already runs resume mode, which sets and clears the key itself.

### Finish take over (new paragraph in rotation.md)

When the rotation check prints `finish:`, the tick prints the follow line, or the hook sends the turn back:

1. Rerun the pass from step 1 in the mode `takeover` names (`take-over`: the four steps; `resume`: resume mode). Step 1 resets `takeover.startedAt`; that is harmless.
2. Skip step 2 when `reset` is already `null` and the mode is `take-over`: step 2 ran, and only steps 3 and 4 are left. With `reset` still set, step 2 runs.
3. Then handle the message that woke this turn as SKILL.md § Turn start says, including its own tick. Steps 3 and 4 are safe to rerun (the tick's rerun rule: each send and start is saved before the next line).

### Step 2 finds the reset message

The reset message becomes **the newest `user_message` that reads `CHIEF OF STAFF RESET`**, not the newest `user_message`. The read stays the same (`itemCount`, then pages of 20 stepping back), and stops at the first match or after 100 items. Then the same checks as today: `senderThreadId` is this thread, and the id equals `reset.id`. An older reset message has an older id and fails the id check, so finding a match further back does not weaken the check. No match within 100 items is `Reset message not recognised; ignoring it.` as today.

The id check still runs once, before `reset` is cleared: a finish rerun skips step 2 only after it already cleared `reset`.

### SKILL.md § Turn start

One new bullet at the top of the list: a message that arrives while a take over runs, or any turn where the tick prints `follow rotation.md § Thread rotation: Finish take over` or the rotation check prints `finish:`, finishes the pass first (rotation.md § Thread rotation "Finish take over") and then gets its answer. The table row `run … cos_rotation_check.py` in § Tick names `finish:` beside `rotate:`.

### What the acceptance looks like

| Case | What happens |
|---|---|
| Title refresh request arrives mid-pass; the model answers it and tries to end the turn | Stop hook sees `takeover`, blocks with `finish: …`; the model finishes steps 3 and 4 in the same turn and posts `Take-over done.` |
| The hook already fired once this stop, or the turn ended anyway | Next turn's tick prints the follow line; the pass finishes, then the message is handled |
| A ticket request (runs no tick) arrives after an abandoned pass | The Stop hook at the end of that turn sends it back to finish |
| Pass abandoned before step 2 | `reset` still set; finish reruns step 2, which finds the reset message under the newer messages, checks the id once and clears `reset` |
| Pass done | `takeover` is null; the rotation check prints `ok context=<N>k` again |

## Tests

Table rows added to existing table-driven tests, no new test files.

- `test_cos_rotation_check.py` `test_decide`: `takeover` set gives `finish: …`, ahead of a fresh `reset` hold and of a size trigger; `takeover` null with the same state gives today's line. The hook test gets one row: `takeover` set blocks once.
- `test_cos_tick.py`: `takeover` set gives the one follow line for `user`, `status` and `notice:` look plans, and no change for `start` or `--after-reads`.
- `test_cos_state.py`: the `takeover` top op accepts null and a valid dict, and rejects a bad mode, a future or zoneless `startedAt`, or extra keys.

## Leaves out

- The reset trigger, its size cap and skill-change rules.
- Cursor and Codex reset support (CW-341, CW-342, CW-343).
- kill-switch.md § Resume (a plain `take over` that passes the user check). It gets no marker.

## Calls I made

- **The Stop hook blocks on an unfinished take over.** The ticket asked for "the tick or the next turn"; the hook also catches it in the same turn, and covers messages that run no tick (ticket requests). It blocks once per stop, as for `rotate:`.
- **Resume mode gets the same marker**, with mode `resume`, because it runs the same steps 3 and 4 and has the same gap. kill-switch.md § Resume does not.
- **The marker is set at step 1, not step 2**, so a pass interrupted before the reset check is caught too. That is the case in the ticket: `reset` was never cleared.
- **A new key, not a longer-lived `reset`.** Keeping `reset` set until step 4 would trip its 10-minute rule mid-pass and print `reset never confirmed`; a separate key leaves the reset rules untouched.
- **Step 2 looks back at most 100 items** for the reset message. Today it steps back until any user message turns up, with no limit.
- **No timeout on `takeover`.** A stuck marker keeps sending turns back to finish, and finishing always clears it.
- **The new line starts `finish:`**, a third kind beside `ok` and `rotate:`, so nothing that reads `rotate:` misreads it.
