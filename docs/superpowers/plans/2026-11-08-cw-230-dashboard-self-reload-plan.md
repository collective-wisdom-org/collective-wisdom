# CW-230 plan: dashboard self-reload

Spec: `docs/superpowers/specs/2026-11-08-cw-230-dashboard-self-reload-design.md`

## Task 1: server version

- `agent-team/scripts/dashboard/server.ts`: export `pageVersion(dir)` (SHA-256 over the `PAGES` files in order, first 16 hex chars, `null` if any file is unreadable). In the `/api` handler, send `{ ...api(), version: pageVersion(join(import.meta.dirname, 'page')) }`.
- `server.test.ts`: one table-driven test for `pageVersion` (same files same version, either file changed differs, missing file `null`) and one check that `/api` has `version === pageVersion(real page dir)`.

## Task 2: page reload

- `page/app.js`: export `versionWatch()` returning `seen(version)`; non-empty string only; first is baseline (false); equal false; different true. In `poll()` after `last = await res.json()`, `if (seen(last.version)) { location.reload(); return }`. One instance next to `poll`.
- `page/app.test.js`: one table-driven test for `versionWatch`.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
