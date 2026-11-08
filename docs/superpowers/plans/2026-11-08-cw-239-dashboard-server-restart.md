# CW-239 plan: dashboard server self-restart

Spec: `docs/superpowers/specs/2026-11-08-cw-239-dashboard-server-restart-design.md`. Follow its Design steps 1 to 9 exactly.

1. `server.ts`: add exported `codeFiles`, `codeVersion`, `restartWatch` (with `failed`), the 5s check loop, preflight import, swap with health wait and rollback, `/health` fields `code` and `pid`, `/api` `restartError`. Tests in `server.test.ts` (three table-driven cases per spec).
2. `page/app.js` `poll()`: show `last.restartError` in `#error` instead of clearing it.
3. `start.ts`: replace a healthy server whose `/health` `code` differs (SIGTERM the `/health` pid, wait for the port, start new). One case in `start.test.ts`.
4. Docs: `chief-of-staff/SKILL.md` line about `dashboard.json`; `README.md` § Local dashboard sentence.
5. Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`. Then hand-prove the swap and the syntax-error case and record it for the PR Proof section.
