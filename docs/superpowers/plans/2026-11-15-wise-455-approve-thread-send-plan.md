# WISE-455 plan: confirm dashboard Approve and Mark todo sends

Spec: [design](../specs/2026-11-15-wise-455-approve-thread-send-design.md). Follow § Design there; this lists the tasks.

1. `server.ts`: `startServer` gains `checkSent?: (thread, command, afterIso) => Promise<boolean | 'unchecked'>`. Default runs `python3 -I <dashboard dir>/../cos_user_check.py latest <thread> --after <iso>` with `execFile`, the command on stdin, 2 s timeout, no shell. `press` reads a JSON body (max 256 bytes) after the origin, site, token and busy checks; `400` unless `command` fully matches `^(approve \d{1,7}|mark \d{1,7} todo)$`. After the press answers `sent`, retry the check every 300 ms up to 3 s: exit 0 -> `{sent:true}`, still 1 -> `{sent:false, reason:'not-recorded'}`, exit 2, error, timeout or no clean `chiefThreadId` in `lastState` (use `cleanThreadId`) -> `reason:'unchecked'`. Other press outcomes answer as today and skip the check. `--after` is the request arrival time as `toISOString()`.
2. `page/app.js`: `pressReturn` POSTs `{command}` as JSON with `Content-Type: application/json`; add `not-recorded` and `unchecked` to `PRESS_MESSAGES` (wording in spec § 2); Approve and Mark todo `title` text gains "and checks it arrived".
3. `README.md` dashboard bullets (lines ~202-211) per spec § 3.
4. Tests (AGENTS.md § Testing, table-driven): `server.test.ts` (existing guard test sends a valid body; one table for the body rule; one for check outcomes incl. press `no-focus` runs no check); `app.test.js` `pressMessage` table gains the two reasons. No change to `cos_user_check.py` or its tests.
5. Run `python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
