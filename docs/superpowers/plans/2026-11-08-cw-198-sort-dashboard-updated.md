# CW-198 plan: sort dashboard sections by last updated

Spec: `docs/superpowers/specs/2026-11-08-cw-198-sort-dashboard-updated-design.md`. Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

1. `agent-team/scripts/dashboard/updated.ts`: `parseUpdated(out, prefix)` and `createUpdated({ run, now })` with `want(cfg)` / `get()` / `idle()`, modeled on `titles.ts`. One `issue list` call, at most one read every 60 seconds, a failed read keeps the last good map.
2. `agent-team/scripts/dashboard/api.ts`: `buildApi` takes `updated` (default `{}`) and reorders each section's non-queued rows newest first. Queued stages (`merge-queued`, `build-queued`, `spec-queued`) keep their places. Rows with no time go last in current order.
3. `agent-team/scripts/dashboard/server.ts`: create `updated` with `ghRunner(root)`, call `updated.want(titleCfg)` in `api()`, pass `updated.get()`.
4. Tests: `updated.test.ts` (shape of `titles.test.ts`) and one table in `api.test.ts`.
5. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
