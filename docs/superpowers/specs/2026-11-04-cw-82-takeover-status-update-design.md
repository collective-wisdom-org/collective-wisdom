# CW-82: Post a status update while the Chief of Staff takes over

**Ticket:** [CW-82](https://github.com/dbeallor/collective-wisdom/issues/82)
**Status:** Shipped
**Shipped:** in PR #90, as specified

## Goal

When the Chief of Staff rotates to a new thread, the user sees a line in the new thread as soon as the take-over is known to be good, instead of nothing until the whole pass ends.

## Today

Facts from `main` at `273fbf9`, checked 2026-11-04.

- `agent-team/.claude/skills/chief-of-staff/rotation.md` § Thread rotation, "Take over", has five steps. Step 1 runs the checks and can wait up to 5 times with `sleep 10` for the old thread's `Moved to` message. Steps 2 to 4 delete the old wake, pin the thread, and run the lean take-over pass (start-up clean-up, idle-check reads, sweep, slot fill). None of them posts anything.
- Step 5 posts the only line: `Chief of Staff moved here from <old thread link>. <N> tickets in flight. Take-over context <K>k.`, plus optional additions (`<M> still under an older thread: ...`, `Filling stopped: <reason>.`) and a report if step 4 found something.
- Step 1 posts `Rotation mismatch: <one line>` or `Rotation mismatch: no Moved to message in <old link>` and stops when a check fails.
- No script or test reads the step 5 line. `grep -rn "moved here"` over `agent-team/`, `docs/agents/`, `README.md` and `AGENTS.md` finds only rotation.md.
- The Moved-to check counts a thread's newest assistant message and passes only when it starts with `Moved to`. Nobody else may start a message that way.
- Resume mode runs take-over steps 2 to 5, not step 1, and posts `Resumed. <N> tickets in flight.` at the end.

## Change

All edits are in `agent-team/.claude/skills/chief-of-staff/rotation.md` § Thread rotation, "Take over".

1. **New line at the end of step 3.** In `take over` only (not resume mode), after `rotation` is set to `null`, post one line as your own reply text (an assistant message, not `t3_thread_send`) before going on to step 4:

   `Taking over from <old thread link>. Checking the tickets in flight; a summary follows.`

   Every `Rotation mismatch` stop, including the re-check of the old thread just before step 3, comes before this point, so a take-over that stops with `Rotation mismatch` posts no "Taking over" line first. Keep going in the same turn after posting it.

2. **Reword the step 5 line** so it doesn't repeat the old thread link the first line already gave:

   `Take-over done. <N> tickets in flight. Take-over context <K>k.`

   The additions (`<M> still under an older thread: ...`, `Filling stopped: <reason>.`) and the report rule stay as they are.

## Calls I made

- The step 5 line drops "Chief of Staff moved here from <old thread link>" and starts `Take-over done.` The ticket allows rewording only if it repeats the first line, and the old link is the part that repeats.
- The first line names only the old thread, not the ticket count. The count needs state work that belongs to step 4, and the final line gives it.
- Resume mode gets no early line. It skips step 1, and the ticket is about rotation. Its `Resumed.` line stays as is.
- The line goes at the end of step 3, not step 1. When the user writes in the new thread while `rotation` is set, take over runs before their command and re-checks the old thread just before step 3, which can end in `Rotation mismatch`. Posting after step 3 means no mismatch can follow the line. Step 2 only deletes a wake, so the line is barely later. (Changed from an earlier draft in code review.)
- Neither line starts with `Moved to`, so the Moved-to check on this thread still fails until a later rotation writes one.
- No tests: the change is prose in a skill, and no script reads either line.

## Leaves out

- How often the thread rotates and how much the skill loads (#53, #23).
- Resume mode's messages.
- Progress lines between the idle-check reads, the sweep and slot fill.

## Verify

- Read the edited "Take over" section: the new line sits at the end of step 3 and applies to `take over` only, and each `Rotation mismatch` path stops before it.
- `grep -rn "moved here" agent-team docs/agents README.md AGENTS.md` finds nothing.
- `python3 -I -m pytest -q agent-team/scripts` passes (no script changes, so this is a guard only).
