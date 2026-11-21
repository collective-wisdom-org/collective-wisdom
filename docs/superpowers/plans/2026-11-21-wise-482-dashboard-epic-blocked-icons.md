# WISE-482 plan: epic and blocked icons on dashboard cards

Spec: `docs/superpowers/specs/2026-11-21-wise-482-dashboard-epic-blocked-icons-design.md` (approved). Build exactly that.

## Task 1: relations read (`agent-team/scripts/dashboard/backlog.ts`, `backlog.test.ts`)
Add the relations read per spec § 1, epic filter, failure behavior, `relations()` accessor. One table-driven test.
Verify: `node --test agent-team/scripts/dashboard/backlog.test.ts`.

## Task 2: rows carry relations (`api.ts`, `server.ts`, `api.test.ts`)
`buildApi` takes `relations`; Ship loop, Todo and Backlog rows get `epic` / `blockedBy` per spec § 2. `server.ts` passes `backlog.relations()` on GitHub, `{}` from the file. Extend the `StatusRow` type.
Verify: `node --test agent-team/scripts/dashboard/api.test.ts agent-team/scripts/dashboard/server.test.ts`.

## Task 3: marks column (`page/app.js`, `page/index.html`, `page/app.test.js`)
Per spec § 3: `rowHead` marks column (avatar, epic slot, blocked icon), CSS, accessible names, escaping. One table-driven test.
Verify: `node --test agent-team/scripts/dashboard/page/app.test.js`.

## Final
`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`. Existing tests must still pass. Test lines must not exceed feature lines.
