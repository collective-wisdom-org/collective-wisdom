# WISE-434 plan: focus the T3 composer before Approve presses Return

Spec: `docs/superpowers/specs/2026-11-15-wise-434-focus-composer-before-approve-design.md` (approved). Follow it exactly; this plan only orders the work.

## Task 0: tests first (table-driven, AGENTS.md section Testing)

- `server.test.ts`: the `pressResult` table gains `no-focus` and `permission` as plain output. The press route rate-limits to one press per 3 seconds and waits 1.2 seconds, so a route row would need a second server; the route only passes the runner's output through `pressResult`, so the table covers it.
- `app.test.js`: the `pressMessage` table gains the `no-focus` row.

## Task 1: server

`server.ts`: `PRESS_SCRIPT` becomes the JXA script (trust check, frontmost check, find the composer, click its centre and warp the mouse back, re-read focus up to 10 times 50 ms apart, press Return). `pressReturnMac` runs it with `osascript -l JavaScript`. `pressResult` maps `no-focus` and `permission` output.

## Task 2: page

`app.js`: `no-focus` line in `PRESS_MESSAGES`.

## Task 3: README

`README.md` section Local dashboard: one sentence on the click and the `no-focus` error line.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
The JXA script was tested by hand on this Mac: `AXFocused` returned success but did not move focus in T3, and the click did.
