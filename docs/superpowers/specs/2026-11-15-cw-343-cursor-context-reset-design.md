# CW-343: Turn on the context reset for Cursor

**Status:** Draft
**Ticket:** [#343](https://github.com/collective-wisdom-org/collective-wisdom/issues/343)

## Goal

A Cursor Chief of Staff resets its own context the way a Claude Code one does: past the size cap, on a skill change or on an agent-gantt plugin change, the rotation check prints `rotate: ...; mode reset`, and the Cursor Stop hook sends that line back into the thread.

## Today

Facts from `main` at `45ef2d78`.

- `RESET_MODES = {"claudeAgent": "reset"}` in `agent-team/scripts/cos_rotation_check.py`. Cursor is missing, so its mode is `none`: `decide()` returns `ok (no reset on cursor; ...)` and never `rotate:`, and `run_hook()` sends a `followup_message` only for `finish:`, `late-child:` or an exit 2 that is not swallowed (on mode `none` an unreadable Cursor store is swallowed as `ok`).
- The two prerequisites the ticket names are in place:
  - **Context size:** CW-341 reads a Cursor Chief of Staff's size from its run store (a floor on the last prompt), so the size trigger has a number to compare.
  - **Recorded reset run:** WISE-441 (which absorbed CW-342) ran a hand reset on Cursor with `t3_thread_send` and `freshContext: true`: same thread id, a new `chiefSessionId` and transcript, and a take over from state (G28). After it, the Cursor Stop hook's `late-child:` answer reached the new session as a `followup_message` and the Chief acted on it (G29).
- What WISE-441 did not show: the size right after the reset (`--record-takeover` printed `size unknown`, G30, [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462), still open), and a `rotate:` line from the hook starting a reset, since mode `none` never prints one.
- Docs that say Cursor has mode `none`: the Cursor cell of the Context reset row and the Fresh-context reset row, the hook bullet under the matrix, the WISE-441 run entry, G8 and G28 in `docs/compatibility.md`, and the end of the Thread rotation paragraph in `agent-team/.claude/skills/chief-of-staff/rotation.md`.
- Tests: `test_line_by_reset_mode` covers modes by provider with made-up providers; `test_hook_on_cursor_answers_with_a_followup_only_for_the_chief_once` has two `cursor` cases that expect silence because Cursor has no reset mode; two other Cursor tests patch `RESET_MODES["cursor"]` or `"p-reset"` to get a reset mode.

## Design

1. **`cos_rotation_check.py`:** `RESET_MODES = {"claudeAgent": "reset", "cursor": "reset"}`. Mode `reset`, not `reset-scheduled`, because the WISE-441 reset used `t3_thread_send` with `freshContext: true` from a Cursor thread. Nothing else in the script changes. The docstring line about `ok (no reset on cursor; size unknown)` becomes a general example (`ok (size unknown on Cursor)` is what a Cursor Chief now prints before its first usage record).
2. **Tests (`test_cos_rotation_check.py`):**
   - In `test_line_by_reset_mode`, add two `cursor` rows with no patching of `RESET_MODES`: over the cap prints `rotate: size 231k >= 220k; mode reset`, and a new skill commit prints `rotate: skill changed aaaaaaa..bbbbbbb; mode reset`. These fail if the entry is removed.
   - In the Cursor hook test, the two `cursor` cases that expected silence now expect a `followup_message` with `rotate: skill changed` (and, for the unreadable store, `rotation-check: cannot read context`). Add a `codex` case so "no reset on this provider: silent" stays covered.
   - Drop the now-redundant `monkeypatch.setitem(crc.RESET_MODES, "cursor", "reset")` in the run-store hook test, and change the plain-mode test's `cursor` row from `ok (no reset on cursor; context=230k)` to `rotate: size 230k >= 220k; mode reset`.
3. **`rotation.md` § Thread rotation:** the sentence "Cursor and Codex have mode `none`" becomes "Codex has mode `none`". The exit-2 fallback's "(Claude Code: `reset`)" becomes "(Claude Code and Cursor: `reset`)". Take over step 4: when `--record-takeover` prints no `take-over context=` (Cursor before the new conversation's first usage record), the post says `Take-over context unknown.` instead of a number, and the 220k Cleanup check is skipped.
4. **`docs/compatibility.md`:**
   - Context reset row, Cursor cell: 🟡 partial: mode `reset` (CW-343), resting on the WISE-441 hand reset (G28) and a `late-child:` followup reaching the reset session (G29); a hook `rotate:` starting a reset is not recorded, and the size after a reset is unreadable (G30).
   - Fresh-context reset row, Cursor cell: drop "mode stays `none`".
   - Hook bullet under the matrix: Cursor now gets `rotate:` too; keep that its payload was checked against Cursor's documented shape and that the `followup_message` path is confirmed only for `late-child:` (WISE-441).
   - G7: Claude Code and Cursor have the hook and mode `reset`; Codex and Antigravity get neither.
   - G8: replace "Its reset mode stays `none`, so ... no skill-change reset" with a sentence that the size now drives the size trigger, and that a floor means it can fire late on a long turn, never early.
   - G28: mode `reset` since CW-343; a hook-started reset on Cursor is still unrecorded.
   - The WISE-441 run entry keeps its "Mode stays `none`" line: it records what was true in that run.

## Leaves out

- Pinning the Cursor review model, and the approval risk tolerance for a Cursor Chief of Staff: `models.md` and `project.md` are not touched, so tolerance stays `strict`.
- Codex and Antigravity reset modes.
- Reading the size right after a reset on Cursor (#462, G30).
- A live Cursor run: this build cannot drive a Cursor Chief of Staff thread, so whether a hook `rotate:` reaches the thread and starts the reset is stated as unconfirmed in the compatibility doc, not proven.

## Acceptance

- `decide()` with `chiefProvider.provider` `cursor` prints `rotate: size <N>k >= 220k; mode reset` over the cap and `rotate: skill changed ...; mode reset` on a new skill commit on `main` on a quiet turn, with no test patching `RESET_MODES`.
- The Cursor Stop hook answers `{"followup_message": "rotate: ...; run chief-of-staff/rotation.md § Thread rotation"}` for the Chief's conversation.
- `RESET_MODES` and the Context reset row agree (both say Cursor is `reset`).
- `models.md` and the approval tolerance are unchanged.
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Calls I made

- **Turning it on before #462 is fixed.** After a reset the new Cursor conversation reads `size unknown` until its first turn with usage, so `--record-takeover` saves no `takeoverContext` and the guard that turns the size trigger off after an oversized take over cannot engage on Cursor. If a reset ever left the context at 220k or more, the check would fire again once the 10-minute reset hold ends. I accept that: WISE-441 showed the reset starts a new Cursor conversation with its own transcript, so the context is fresh by construction, and the size is a floor, so it does not fire early.
- **Rated 🟡 partial, not 🟢.** The hook's `followup_message` is confirmed only for `late-child:`; a `rotate:` from it starting the reset is not recorded, and neither is the post-reset size.
- **No live check in this ticket.** The ticket asks to check that the hook answer reaches the thread and starts the reset; the build has no Cursor Chief of Staff to run, so it records WISE-441's evidence and says what is unconfirmed, as the ticket allows.
- **The plugin-change trigger comes on too.** It rotates in every mode but `none`, so a Cursor Chief also resets to load a newer agent-gantt plugin. I did not exempt Cursor.
- **The exit-2 item-count fallback now applies on Cursor** (reset at 240 or more items when the size cannot be read), since it is gated on a mode other than `none`.
- **`Take-over context unknown.`** wording for the take-over post on Cursor, a small `rotation.md` change the ticket did not name, because step 4 assumed a number.
- **The WISE-441 run record stays as written**, including "Mode stays `none`", since it describes that run.
