# CW-178 plan: dashboard Gantt charts only for worktree sessions

Spec: `docs/superpowers/specs/2026-11-07-cw-178-gantt-worktree-only-design.md`

## Tasks

1. `mods/agent-gantt/hooks/rows.ts`: move the two `repoOf` regexes into module constants; add exported `isWorktree(cwd)` that is true when either matches; `repoOf` uses the same constants and returns what it does now.
2. `agent-team/scripts/dashboard/api.ts`: import `isWorktree` from `../../../mods/agent-gantt/hooks/rows.ts`; `cleanSnapshot` returns `null` when `!isWorktree(str(s.cwd))`.
3. `agent-team/scripts/dashboard/api.test.ts`: change the `snapshots` test's `cwd` from `/c` to a worktree path; add one table-driven test with three cases (T3 worktree kept, `.worktrees/` kept, root checkout dropped). Fix any other test file whose snapshots use a non-worktree cwd (`server.test.ts`, `page/app.test.js` if they go through `buildApi`).

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
