# CW-198: Sort dashboard tickets in each section by last updated

**Status:** Draft
**Ticket:** [#198](https://github.com/collective-wisdom-org/collective-wisdom/issues/198)
**Related:** #195 changes the page markup and layout; this ticket changes only the order of rows that `/api` returns.

## Goal

Inside each dashboard status section, the ticket the tracker saw change most recently sits on top. The queued sections keep their start order, because that order is the queue.

## Today

Facts from `main` at `19f815d`.

- `buildApi` in `agent-team/scripts/dashboard/api.ts` turns `groupTickets(state)` (`agent-team/.claude/mods/status-pane/hooks/groups.ts`) into `status: { name, count, rows }[]`. Each row carries its state `stage`.
- `groupTickets` sorts each section by stage, then by `queuedAt`. Only queued stages set `queuedAt`, so every other section is in `state.json` order.
- The `Other` section holds two stages: `spec-queued` (a queue) and `blocked`.
- `state.json` has no last-updated time. Each GitHub issue has an `updatedAt`.
- `titles.ts` shows the background read pattern: `gh.sh` through `ghRunner(root)`, one read at a time, results cached, a failure retried later, `/api` never waits.
- `server.ts` reads `docs/agents/project.md` on each `/api` call and builds `titleCfg` (`prefix`, `slug`) only when tickets are GitHub issues.

## Builds

1. **`agent-team/scripts/dashboard/updated.ts`**, next to `titles.ts`.
   - `parseUpdated(out, prefix)` reads the JSON list `[{ number, updatedAt }]` and returns `Record<string, number>`: `<prefix>-<number>` to epoch milliseconds. Entries without an integer `number` or a parseable `updatedAt` are dropped. Bad JSON returns `{}`.
   - `createUpdated({ run, now })` returns `want(cfg)` and `get()`. `want` starts one background read when none is running and the last attempt was 60 seconds ago or more:
     `issue list --repo <slug> --state all --limit 100 --search sort:updated-desc --json number,updatedAt`.
     A good read replaces the map. A failed read keeps the last good map; the next try comes 60 seconds later. `get()` returns the current map and never waits.
2. **`server.ts`** calls `updated.want(titleCfg)` in `api()` next to `merged.want`, and passes `updated: updated.get()` to `buildApi`. With no `titleCfg` (no project file, or a tracker other than GitHub issues) nothing is read and the order stays as today.
3. **`buildApi`** takes an optional `updated: Record<string, number>` (default `{}`). After it builds each section's rows, it reorders them:
   - Rows whose stage is queued (`merge-queued`, `build-queued`, `spec-queued`) keep their places.
   - The other rows are sorted newest `updated` time first and put back into the remaining places. A row with no time goes after every row with one. The sort is stable, so rows with no time, and rows with the same time, keep today's order.
   - `count` is unchanged.
   So `Queued to merge` and `Queued to build` are untouched, and in `Other` the `spec-queued` rows stay first in start order while the `blocked` rows below them go newest first.
4. **Tests.**
   - One table-driven test in `api.test.ts` for the reorder: newest first, missing time last in state order, the two queued sections unchanged, and `Other` with `spec-queued` rows kept in place.
   - One test in `updated.test.ts`, in the shape of `titles.test.ts`: a good read fills `get()`, a bad entry is dropped, a failed read keeps the last good map, and no second read starts before 60 seconds.

## Leaves out

- The status-pane mod and its `groups.ts` ordering.
- The Merged list and the order of Gantt sessions inside a card.
- Any change to the page markup, layout or `app.js` (#195 does that).
- Showing the updated time on the page.
- Trackers other than GitHub issues (Linear, Jira). Their sections keep today's order.

## Calls I made

- **`Other` is split, not sorted as a whole.** It mixes `spec-queued` (a queue) and `blocked`. The `spec-queued` rows keep their start order and their places; only the `blocked` rows sort newest first. The rule is per stage, not per section name, so a future queued stage in a mixed section is safe too.
- **One list call per minute, not one `gh issue view` per ticket.** The ticket said to read the way `titles.ts` does. I kept its pattern (background, cached, one read at a time, failure retried, `/api` never waits) but read all times in one `gh issue list` call sorted by update time, limit 100, every 60 seconds. Per-ticket reads on a board of ten would be about ten calls a minute against the user's GitHub rate limit; this is one. A board ticket outside the 100 most recently updated issues has no time and sorts last, which is where its time would put it anyway.
- **Refresh every 60 seconds.** Titles are read once and kept, but update times change, so they must be read again. 60 seconds is 12 polls of the page. A ticket's new place can lag its update by up to about a minute.
- **`--state all`**, so a ticket that was closed but is still on the board gets a time.
- **Tracker `updatedAt` is the only clock.** State changes that don't touch the issue (a child's status line) don't move a ticket up. That is what the ticket asked for.
- **Only GitHub-issues repos get times.** The read reuses `titleCfg`, which exists only when tickets are GitHub issues, so an app on Linear or Jira sees today's order and no failing `gh` calls.

## Touches

None of these: data, money, auth, user email, migrations.
