# CW-325 plan: keep the spec phase on a ticket gantt after the build session starts

Spec: `docs/superpowers/specs/2026-11-14-cw-325-keep-spec-gantt-rows-design.md` (approved). Follow its Design steps 1 to 5. Test budget: `AGENTS.md` § Testing, one table-driven test per rule; test lines do not exceed feature lines.

## Task 1: snapshot.ts
Add `earlierRows(old: unknown, mainStart: number): Row[]`. It returns `[]` unless `old` is an object with a `rows` array and a numeric `updatedAt`. It keeps rows that are objects with a string `id` and a numeric `start` below `mainStart`, prefixes each id with `r<updatedAt>:`, and closes each at `updatedAt` (an `end` of null becomes `updatedAt`; a segment with a null end ends at `max(start, updatedAt)`). Add `oldFields(old, sessionId)` or similar only if it keeps `register.tsx` short: it returns the old `heading`, `ticket` and `request` (strings or null), and nothing when `old.sessionId` is not this session's. `earlierRows` also returns nothing for a wrong `sessionId` when the caller passes one; the check can live in one place.
Test: one table in `snapshot.test.ts` (restart, no restart, second restart, bad old snapshot, wrong session, running row) plus one case running `earlierRows` and `buildSnapshot` together: spec rows come first, then build rows.
Verify: `node --test mods/agent-gantt/hooks/snapshot.test.ts`

## Task 2: register.tsx
Module variable for the old parsed snapshot (`undefined` until read). In `writeSnapshot`, after the link and folder checks, read `<dir>/.agent-team/gantt/<name>` once (try/catch, JSON.parse, any failure gives null). Use `earlierRows` with the current `main` row's `start` and write `[...earlier, ...rows]`. When the current heading, ticket or request is null, use the old file's value.
Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Final
`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
