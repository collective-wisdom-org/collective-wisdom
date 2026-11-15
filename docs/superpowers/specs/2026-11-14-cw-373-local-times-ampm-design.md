# CW-373: Show every dashboard time in local time, am/pm, with no timezone

**Status:** Draft
**Ticket:** [#373](https://github.com/collective-wisdom-org/collective-wisdom/issues/373)

## Goal

Every clock time on the dashboard reads in the viewer's local time as `h:mm am/pm`, with no timezone name. That includes times inside the status text the Chief of Staff writes, which are UTC today (`build since 3:55am UTC`).

## Today

Facts from `main` at `360a03d`.

- `clock(ms)` in `agent-team/scripts/dashboard/page/app.js` builds local `h:mm am/pm` from `getHours()` and `getMinutes()`. `stamp()` and `dayWords()` are local too. Every time the page builds from an ISO timestamp (`stageAt`, `mergedAt`, updated, run ranges, the wait tooltip) is already local and shows no zone.
- `row()` in `agent-team/scripts/dashboard/groups.ts` splits the state `status` line at `Risk:` into `next` and `risk`. `api.ts` passes both through. The page prints `next` on the card (`<p class="next">`) and in the Details panel (`Next`), and `risk` as the risk badge or plain risk text and in Details (`Risk`). These are the only state or status text the page shows. The Chief of Staff tab and the project manager rows show only a role, a state word and times the page builds.
- Status lines in today's state carry times written three ways: `3:55am UTC`, `3:53am` (UTC, no marker) and, in the docs' examples, `14:05` (24-hour, UTC). The Chief of Staff writes them in UTC (`chief-of-staff/SKILL.md` § State file uses UTC throughout).

## Design

### One conversion, in the page

A new exported function in `app.js`, `localTimes(text, now)`, finds each clock time in a piece of text and replaces it with `clock(ms)` of that time read as UTC. The page is the only place it runs: it is the only side that knows the viewer's timezone, and the server keeps passing the text through unchanged. `groups.ts` and `api.ts` do not change.

A clock time is:

- an hour of 1 or 2 digits, `:`, two minute digits,
- then optionally `am` or `pm` (any case, with or without a space before it),
- then optionally ` UTC` or `Z`, which is dropped.

Not a clock time: digits right before or after (`2026-11-02T09:30:00Z`, `10:30:00`), an hour above 23, a minute above 59, or an hour above 12 with `am`/`pm`. Those are left as they are.

With `am`/`pm`, 12 am is hour 0 and 12 pm is hour 12. Without it, the hour is 24-hour.

### Which day

A status time has no date. The conversion takes the latest moment at or before `now` (plus one minute, for clock skew) whose UTC hour and minute match, and shows `clock()` of it. Status times are "since" times, so they are in the past. This keeps the result right across midnight and daylight saving changes, since the offset is the one in force at that moment.

### Where it applies

- The card's `next` line and the Details `Next` value.
- The risk text, plain or badge, and the Details `Risk` value. A risk is read for its level word first, so a time never changes the level.

The text is converted, then escaped, as today.

### Tests

One table-driven test in `page/app.test.js` that sets `process.env.TZ` to `America/Toronto` for its run and restores it after. It checks `localTimes` with a fixed `now`:

- `build since 3:55am UTC: child building` → `build since 10:55 pm: child building` (the day before, in Toronto),
- a pm time (`2:05pm UTC` → `9:05 am`),
- `12:00am UTC` and `12:00pm UTC`,
- a bare 24-hour `14:05`,
- an ISO timestamp, `10:30:00` and `25:00` (unchanged),
- text with no time (unchanged).

One render check: a card whose `next` is `build since 3:55am UTC: x` shows the converted time and no `UTC` in the card or its Details.

## Leaves out

- What the Chief of Staff writes into `status` lines, and the examples in `chief-of-staff/state-keys.md` and `status.md`. Times in state files stay UTC.
- A timezone or 12-hour versus 24-hour setting.
- `UTC` times printed by scripts outside the dashboard (`cos_state.py`, `cos_idle_check.py`, `release_notes.py`).
- Times the page already builds from ISO strings: they are local already.
- Ticket titles and spec or PR text in the Details panel: they are the author's words, not state or status text.

## Calls I made

- **Every clock time in status text is read as UTC, marker or not.** Today's state has `3:53am` with no marker next to `3:55am UTC`, and the docs show bare `14:05`. All come from the Chief of Staff, which writes UTC. A time someone wrote in local time without a marker would show shifted.
- **The day is the latest past match before now.** A status line has no date, so a time later than the current UTC clock is taken as yesterday's.
- **The conversion runs in the page only,** not in `groups.ts` or `api.ts`. The ticket asks for one place; the page is where the viewer's timezone is known.
- **Risk text is converted too.** It is the other half of the same status line.
- **Spec and PR text in Details is not converted.** It is long-form writing, where a time may be an example or not UTC.
- The test pins `America/Toronto`, which is behind UTC, so a morning UTC time lands on the day before.

## Touches

None of: data, money, auth, user email, migrations. Display only; state files are unchanged.
