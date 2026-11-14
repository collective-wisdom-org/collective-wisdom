# CW-296 plan: top Backlog tickets on the Ship loop tab

Spec: `docs/superpowers/specs/2026-11-13-cw-296-top-backlog-design.md` (approved). Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: `backlog.ts`

- Add `createdAt` to the `issue list --json` fields.
- `BacklogItem` gains `priority` (`urgent|high|medium|low|null`, from `priority:<x>` labels, unknown ignored, highest wins) and `createdAt` (ms, null when missing or unparseable).
- Test: one table for the priority and `createdAt` parse.

## Task 2: `api.ts`

- Backlog group only: sort by priority, then `createdAt` newest first (missing last), then tracker order; keep 3. `count` stays the full number after the in-state and merged skips. Todo is unchanged.
- The Backlog group gets `moreUrl: <repo.url>/issues` when `repo.isGithubIssues`; no other group does.
- Test: one table for the Backlog group (order, short list, count, `moreUrl` present or absent, Todo not cut).

## Task 3: `page/app.js`

- `renderStatus`: after the rows, inside the group's `<details>`, draw `Full backlog` when `moreUrl` is `http(s)`, escaped and opened like other issue links.
- Test: link rendered and escaped; a non-`http(s)` `moreUrl` draws none.

## Task 4: README

- § Local dashboard: replace the Not started band sentence per the spec (§ 4).

## Verify

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` (Node 24+).
