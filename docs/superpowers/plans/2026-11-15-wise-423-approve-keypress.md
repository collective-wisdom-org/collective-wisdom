# WISE-423 plan: Approve presses Return in T3 Code

Spec: `docs/superpowers/specs/2026-11-15-wise-423-approve-keypress-design.md` (approved). Follow it exactly; this plan only orders the work.

## Task 0: tests first (table-driven, AGENTS.md § Testing)

- `server.test.ts`: one table for the `POST /press-return` guard (good origin+token presses once; missing/other origin, cross-site, missing/wrong token, wrong Host, GET, OPTIONS do not call the runner; second press within 3 s answers `busy`); one table for `pressResult`; token present in `/` and absent from `/api` and `/health`.
- `app.test.js`: approve-controls table (`data-return` and new title on Approve with a thread link only), one table for the message line per `reason`.

## Task 1: server

`server.ts`: per-process token (`randomBytes`), injected into `/` as the meta tag, `POST /press-return` with all six checks, `timingSafeEqual`, 3 s rate limit, 1.2 s wait, `osascript` through `execFile` with the fixed script, `pressResult`, optional `pressReturn` in `startServer` options. Add the meta placeholder to `page/index.html`. Update the CSP only if needed (same-origin fetch needs none).

## Task 2: page

`app.js`: `data-return` and title on the Approve link, click handler (let the link open, blur it, POST with token header, show the message in `#error`).

## Task 3: README

`README.md` § Local dashboard per the spec's Docs section.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
Then the real run on this Mac (spec § Test, § Calls): throwaway thread only, never the live Chief of Staff thread. Report what happened, including where focus lands.
