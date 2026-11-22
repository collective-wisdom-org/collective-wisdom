# WISE-495 plan: dashboard thread links that blank the T3 window

**Spec:** `docs/superpowers/specs/2026-11-22-wise-495-dashboard-links-blank-window-design.md`
**Test command:** `python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Task 0: tests first
- `page/app.test.js`: `promptLink` table gains rows for ids with `%3A` and `.` (expect `%253A` and `%2E`), and `pressMessage` gains a `not-open` line for both actions.
- `server.test.ts`: `pressResult` table maps `not-open` to `{ sent: false, reason: 'not-open' }`; the press-return table gains a `not-open` row that runs no check.

## Task 1: link shape (`page/app.js`)
Encode both segments of `promptLink` with `encodeURIComponent` plus `.!~*'()` as `%XX` (T3's own encoder). Rewrite the comment: checked against T3 Code 0.1.9 and 0.1.10-nightly; opens through the built-in browser's "Open this t3code link?" dialog; T3 decodes route segments, so raw `%` in an id would be decoded twice.

## Task 2: press only into the open Chief of Staff thread (`server.ts`, `page/app.js`)
- JXA script: poll up to 5 s. Each try: not front -> `not-frontmost`; a sheet (`AXSheet` child of the focused window) or a composer whose `AXDescription` lacks `Chief of Staff` -> `not-open`; otherwise the existing focus and Return. Retry on those two, return the last one at the end. Re-check for a sheet right before Return.
- Drop the 1.2 s sleep before the script; `execFile` timeout 3 s -> 8 s; `pressResult` accepts `not-open`.
- `PRESS_MESSAGES['not-open']`: `<action> not sent: the Chief of Staff thread was not open yet. Press Send there.`
- README § Local dashboard: replace "about 1.2 seconds after the click" with the 5 second wait and the not-open case.

## Task 3: live reproduction and the fallback rule
Run the spec's step 1 on the running Nightly; put the observations in the PR `## Proof`. If T3 cannot open the thread (blank pane) even with encoded ids, apply spec step 4 (controls become copy buttons).
