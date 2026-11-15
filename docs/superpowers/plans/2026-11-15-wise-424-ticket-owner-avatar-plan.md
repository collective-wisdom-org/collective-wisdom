# WISE-424: ticket owner avatar, plan

Spec: [2026-11-15-wise-424-ticket-owner-avatar-design.md](../specs/2026-11-15-wise-424-ticket-owner-avatar-design.md)

## Task 1: owner and viewer data (server side)

Files: `agent-team/scripts/dashboard/{merged,open,backlog,titles,api,server}.ts` and their tests.

1. `merged.ts`, `open.ts`: request `author`; parse a valid login (`^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`) as `owner` (merged entry) or an owner map (open; higher PR number wins). `backlog.ts`: `BacklogItem.owner`. `titles.ts`: read `title,author`, add an owner getter.
2. `api.ts` `buildApi`: `owner` on Done entries, status rows (open PR author, else issue author, else none) and Todo/Backlog rows; none on helper and project manager rows. Pass owners in as new inputs.
3. `server.ts`: read the viewer once with `gh api user --jq .login`, retry at most every 5 min on failure; add `viewer` to `/api`; CSP gains `img-src 'self' https://avatars.githubusercontent.com`.
4. Tests: one table per rule in `merged.test.ts`, `open.test.ts`, `api.test.ts`, `server.test.ts` (CSP).

## Task 2: page

Files: `page/app.js`, `page/index.html`, `page/app.test.js`.

1. `ownerBadge(login)`, `foreign(owner, viewer)` exported; `rowHead` takes the badge; `panelSwitch` takes `hideAgents` (leaves out Agents only when the Gantt has no tasks).
2. `ticket()`, `renderMerged()`, `renderStatus`, `renderBacklog` take `viewer`; the shell passes `last.viewer` and redraws when it changes; a capture-phase `error` listener hides a failed `.avatar img`.
3. CSS for `.owner`, `.avatar`, `.initial`, `.login` (20px circle, truncating login).
4. One table-driven `app.test.js` test as the spec lists.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
