# CW-348 plan: current dashboard ticket titles

Spec: `docs/superpowers/specs/2026-11-14-cw-348-current-ticket-titles-design.md`. Test: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.

## Task 1: titles.ts refreshes titles

- Add `REFRESH_MS = 60_000`. Keep a map of the time of each good read.
- `want`: skip an id when it is queued, fails the prefix shape, or failed within `RETRY_MS`; also skip when it has a title read less than `REFRESH_MS` ago. Otherwise queue it.
- `drain`: a good read replaces title and time (and clears the failure); a failed or empty read keeps the old title and sets the failure time.
- Extend the table test in `titles.test.ts`: re-read only after 60s with the new title replacing the old; a failed re-read keeps the last good title and is not retried before 5 minutes.

## Task 2: server.ts asks for every ticket

- Remove the `blank` filter; pass all ticket ids to `trackerTitles.want`.

## Task 3: api.ts tracker title wins

- Row title: `titles[r.id] || r.title || ''`.
- Update the `row title` test in `api.test.ts`: tracker wins over state; state when the tracker title is missing; empty when neither.

## Task 4: docs

- Reword the `title` line in `agent-team/.claude/skills/chief-of-staff/state-keys.md`: the dashboard shows the tracker's current title and falls back to this one.
