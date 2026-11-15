# CW-373 plan: local am/pm times in dashboard status text

Spec: `docs/superpowers/specs/2026-11-14-cw-373-local-times-ampm-design.md`. Only `agent-team/scripts/dashboard/page/app.js` and `page/app.test.js` change.

## Task 1: `localTimes` and its use

1. In `app.js`, after `clock`, add exported `localTimes(text, now = Date.now())` per the spec § One conversion and § Which day: match `(?<![\d:])(\d{1,2}):(\d{2})(?!\d|:)\s?(am|pm)?(?:\s?UTC|Z)?` case-insensitively; leave a match alone when the hour or minute is out of range, or the hour is above 12 with am/pm, or the char before/after is part of a longer number or time. Compute the latest UTC moment at or before `now + 60_000` with that hour and minute, and return `clock(ms)`.
2. Apply it (before `esc`) to `r.next` in the card (`<p class="next">`) and Details `Next`, and to the risk text in `riskText` output (`text`) and Details `Risk`. The risk level is read from the raw text first.
3. Tests in `page/app.test.js` per spec § Tests: one table-driven `localTimes` test under `TZ=America/Toronto` (set and restore `process.env.TZ`), and one render check that a card and its Details show the converted time and no `UTC`.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, then `python3 -I -m pytest -q agent-team/scripts`.
