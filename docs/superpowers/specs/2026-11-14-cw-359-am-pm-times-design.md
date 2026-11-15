# CW-359: Show times in 12-hour am/pm format everywhere

**Status:** Draft
**Ticket:** [#359](https://github.com/collective-wisdom-org/collective-wisdom/issues/359)

## Goal

Every time a person reads on the dashboard, in the agent-gantt pane or in the agent scripts' text output shows as 12-hour time with am/pm (`2:05 pm`), not 24-hour (`14:05`). ISO timestamps that code reads or writes stay as they are.

## Today

Facts from `main` at `247d285`.

- `clock(ms)` in `agent-team/scripts/dashboard/page/app.js` and in `mods/agent-gantt/hooks/format.ts` return local `HH:MM`. The dashboard uses it for "since" on stage sentences, "merged", "updated", run ranges, and the `stamp()` date-time string.
- `t()` in `agent-team/scripts/cos_state.py` prints `%H:%M` (UTC) for a time on today's UTC date in `show` and in `observe` notes, and the full ISO string for other days.
- `hhmm()` in `agent-team/scripts/cos_idle_check.py` prints `%H:%M` (UTC) in its `ok`, `full` and `waiting` lines.
- `release_notes.py` prints `Merged YYYY-MM-DD HH:MM UTC.` under each note. `merge_pr.py` publishes that text to `RELEASE_NOTES.md`.
- `agent_usage.py` prints `Window YYYY-MM-DD HH:MMZ to YYYY-MM-DD HH:MMZ`.

### What reads these strings

Checked before changing any of them:

- No script parses any of the display times above. They reach people and agents only: the Chief of Staff reads `cos_state.py show` and `cos_idle_check.py` lines and acts on the leading word (`ok`, `full`, `waiting`, `stalled`) and the ticket id, never on the time. The project-manager ranking child gets the `merged` times as context.
- The state file, `stageAt`, `lastSeenAt` and every other stored time are ISO strings (`%Y-%m-%dT%H:%M:%SZ`) and do not change. `cos_state.py show` keeps printing the full ISO string for a time not on today's date, which `test_cos_state.py` asserts.
- Existing tests that assert the old display text (`test_cos_idle_check.py`, `test_release_notes.py`, `dashboard/page/app.test.js`) change to the new text. They check display, not a parsed value.

## Design

### One rule

Hour `h` (0 to 23) and minute `m` show as `{h % 12 or 12}:{m:02d} {am|pm}`: no leading zero on the hour, lower-case `am` before noon and `pm` from noon. Midnight is `12:00 am`, noon is `12:00 pm`, `00:30` is `12:30 am`, `09:05` is `9:05 am`, `23:59` is `11:59 pm`.

### Dashboard and gantt pane

- Both `clock(ms)` helpers return the rule above in local time, as today. Every caller gets the new text with no other change.
- `stamp()` keeps its `YYYY-MM-DD` date and gets the new time: `2026-01-02 3:04 am`.
- Tests: one table-driven test per helper, covering `12:00 am`, `12:30 am`, `9:05 am`, `12:00 pm` and `11:59 pm`. The existing app tests that assert `09:05` or `03:04` change to `9:05 am` and `3:04 am`.

### Scripts

- A new shared module `agent-team/scripts/clock12.py` with one function `clock12(dt)` that applies the rule to a `datetime` as given (callers convert to UTC first, as they do today). The four scripts import it the way they import `app_root`.
- `cos_state.py` `t()`: `2:05pm` for a time on today's UTC date (see Calls I made on the missing space). The full ISO string for other days stays.
- `cos_idle_check.py` `hhmm()`: `2:05 pm UTC`, so `ok ABC-1 (running, updated 4:49 am UTC)`. It is UTC today with no marker; the marker is added because a reader in another time zone would otherwise take it for local time.
- `release_notes.py`: `Merged 2026-11-04 9:00 am UTC.` The UTC marker stays. Every published note changes format on the next merge, since `merge_pr.py` rewrites the whole `RELEASE_NOTES.md`.
- `agent_usage.py`: `Window 2026-11-04 9:00 am UTC to 2026-11-04 5:30 pm UTC`. The `Z` marker becomes ` UTC`, because `5:30 pmZ` does not read.
- Tests: one table-driven test for `clock12` with the same five cases. The existing idle-check and release-notes assertions change to the new text.

## Leaves out

- A setting to switch between 12-hour and 24-hour.
- Dates and time zones: the dashboard and pane stay local, the scripts stay UTC.
- ISO timestamps in state files, tracker lists, gantt files and any machine-read output.
- `HH:MM` slices of GitHub `createdAt` in `cos_brief.py` and `cos_handoff.py` review lines (`(21:02)`). They are not in the ticket's list and are read by child agents, not shown to the user.
- `status` text the Chief of Staff writes into state (`awaiting-merge since 14:05: ...`) and the examples of it in `chief-of-staff/state-keys.md` and `status.md`. That is free text an agent writes, not script output.
- Durations (`2h 05m`, `50m`).

## Calls I made

- **`cos_state.py show` drops the space: `seen=2:05pm`.** `show` prints `key=value` pairs separated by spaces, so `seen=2:05 pm` would read as a value `2:05` followed by a stray `pm`. Everywhere else uses `2:05 pm` as the ticket shows.
- **`cos_idle_check.py` gains a `UTC` marker** it does not have today, and `agent_usage.py`'s `Z` becomes ` UTC`. The ticket says keep the marker where it is; these two are the closest readable form.
- `cos_brief.py` and `cos_handoff.py` review-line times stay 24-hour (Leaves out). Easy to add if you want them too.
- One shared Python module (`clock12.py`) rather than the same three lines in four scripts.
- Lower-case `am`/`pm` with a space, no leading zero on the hour, matching the ticket's example.
- Existing tests that assert old display text are updated, not kept, since they check display only.

## Touches

None of: data, money, auth, user email, migrations. State files and stored timestamps are unchanged.
