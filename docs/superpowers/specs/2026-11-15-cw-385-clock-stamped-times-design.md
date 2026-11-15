# CW-385: Stamp status-line times and approval-comment times from the clock

**Status:** Shipped
**Shipped:** in PR #403, as specified
**Ticket:** [#385](https://github.com/collective-wisdom-org/collective-wisdom/issues/385)

## Goal

The Chief of Staff stops typing clock times. A ticket's `status` line gets its `since` time from the same stamp as `stageAt`, and every time the Chief of Staff writes into a ticket comment comes from a script that reads the clock. A wrong time then can't mislead the Chief of Staff the way it did on CW-348.

## Today

Facts from `main` at `6e20485`.

- `cos_state.py` stamps `stageAt` with `now()` (ISO, UTC) on `start` and on a `stage` op that changes the stage, and rejects a `set` or `stage` op that names `stageAt`.
- `status` is free text the model passes on `start`, on every `stage` op, and in a `set`. The examples in `chief-of-staff/state-keys.md` (the state example and the `status` key), `SKILL.md` § State file, `status.md` and `approvals.md` (the `awaiting-review` line) all show a hand-typed `<stage> since 14:05: ...`.
- Ticket comments with a model-typed `<time>`:
  - `approvals.md` § Ticket comment on approval: `the user approved the <spec|merge> at <time>` and `auto-approved the <spec|merge> at <time> ...`.
  - `review.md`: `the user approved the merge at <time>: ... Held until a teammate approves this head.`, and the `heldApproval` value `{"head", "itemId", "at": "<time>"}` it sets.
  - `commands.md` (`cancel N`, `hold N`, `changes N`) and `send-or-queue.md` (four lines): `Approval withdrawn at <time>: ...`.
- Times that already come from script output and stay as they are: `changes ... at <time>` from `cos_review_check.py` (and the `changesRelayed.at` copied from it), `merged ... at <time>` from the merged check, `merged.at` (stamped by the `merged` op).
- `clock12.py` `clock12(dt)` formats `2:05 pm`. `cos_idle_check.py` and `release_notes.py` add ` UTC`; `release_notes.py` prints `2026-11-04 9:00 am UTC`.
- The "take timestamps from `date -u`" line the ticket mentions is not in `agent-team/`, the machine install at `~/.collective-wisdom`, `~/.claude/CLAUDE.md`, `~/.cursor/rules` or this repo's memory. There is nothing to remove.
- Readers of `status`: `cos_handoff.py` (copies it, capped), `cos_approve_pr.py` (passes it through), the dashboard `groups.ts` (splits on `Risk:`, shows the rest). None parses the time.

## Design

### One time format

`cos_state.py` gets `stamp_text(iso)`: `YYYY-MM-DD h:mm am|pm UTC` (the date, then `clock12`, then ` UTC`), e.g. `2026-11-15 5:16 am UTC`. It is the same shape `release_notes.py` prints. The date is there because a status line stays in state for days, and a bare `5:16 am` read the next day points to the wrong day.

### Status lines: a `{since}` placeholder

- `start`, `stage` and `set` (when it sets `status`) replace every `{since}` in the status text with `stamp_text(stageAt)`, using the ticket's `stageAt` after the op (so a stage change gets the new stamp, and a same-stage op or a `set` gets the current one). The two can't differ, because the script writes both from one value.
- A status with a hand-typed time is rejected: `since` followed by a digit, before the first `"` in the text (quoted words, such as a `BLOCKED:` line, are left alone). The reject message says to use `{since}`. A status without `since` at all stays allowed; the docs say to start every status with `<stage> since {since}: `.
- The docs change every example to `<stage> since {since}: ...`: `state-keys.md` (state example and the `status` key), `SKILL.md` § State file, `status.md` (its example row shows the stamped result), and `approvals.md`'s `awaiting-review` line.

### Comment times: `cos_state.py now`

- A new subcommand `cos_state.py now` prints the current time in the same format (`2026-11-15 5:16 am UTC`) and reads no state file. `now --iso` prints the ISO form `now()` writes into state (`2026-11-15T05:16:00Z`).
- `approvals.md` § Ticket comment on approval says the `<time>` in both comments is the output of `python3 ~/.collective-wisdom/scripts/cos_state.py now`, run just before posting. The `Approval withdrawn at <time>` lines in `commands.md` and `send-or-queue.md`, and the held-approval comment in `review.md`, point to the same rule.
- `heldApproval.at` is stamped by `cos_state.py`: a `set` that gives `heldApproval` without `at` gets `at = now()`, and one that names `at` is rejected, as for `stageAt`. `review.md` and the `state-keys.md` `heldApproval` key drop `"at": "<time>"` from what the model sends. The other `heldApproval` checks (full `head` equal to `headSha`, an `itemId`, only in `awaiting-review`) stay.

### Tests

In `test_cos_state.py`, one table-driven test for the rule "the `since` time in a status is the ticket's `stageAt`": for `start`, a stage change, a same-stage `stage` op and a `set` of `status`, apply the op with `{since}` in the status, then assert the saved status contains `stamp_text(saved stageAt)`; plus a row with a hand-typed `since 5:20am` that must be rejected and a row with `since 5` inside quotes that must be kept. One test that `heldApproval.at` is stamped and that a given `at` is rejected. Existing tests that build a `heldApproval` with `at` change to leave it out.

## Leaves out

- Dashboard time display (CW-373).
- Which stages stamp `stageAt`.
- Rewriting status lines already in a state file. They keep their old text until the next `stage` op writes a new one.
- Times the Chief of Staff copies from script output (`changes ... at`, `merged ... at`, `changesRelayed.at`, `merged.at`).
- Times in the Chief of Staff's own chat reports to the user, beyond the status lines they copy.

## Calls I made

- Hand-typed times in a status line are rejected, not just discouraged. A `since <digit>` inside a quote is allowed, so a quoted `BLOCKED:` line can't trip it.
- `heldApproval.at` is stamped by the script, and an `at` the model sends is rejected. That changes the op shape the Chief of Staff sends; the ticket did not ask for it, but it is the one other clock time the model types into state.
- The `Approval withdrawn at <time>` comments use `cos_state.py now` too, though the ticket names only the approval comments: its acceptance says no skill file tells the model to type a clock time.
- The format carries the date and ` UTC`: `2026-11-15 5:16 am UTC`, the shape `release_notes.py` already prints. Status lines get longer by about 11 characters.
- The time-printing command lives in `cos_state.py` (`now`), not in a new script, so the Chief of Staff has one script for state and times.
- The placeholder is `{since}`, as the ticket suggests. The script replaces it rather than prepending `<stage> since ...` itself, so status lines keep their free shape.
- The `date -u` line could not be found anywhere I can read, so nothing is removed for it.
