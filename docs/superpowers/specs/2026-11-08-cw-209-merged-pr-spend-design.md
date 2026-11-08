# CW-209: Show agent spend on the merged PRs in the dashboard

**Status:** Shipped
**Shipped:** in PR #211, with differences: [as-built](../as-built/2026-11-08-cw-209-merged-pr-spend-as-built.md)
**Ticket:** [#209](https://github.com/collective-wisdom-org/collective-wisdom/issues/209)
**Related:** #187 added the merged list; #195 and #200 set the page layout this row fits into.

## Goal

Each row in the dashboard's merged list shows what the agents spent on that ticket, in the same `$1.23` and `4.5M tokens` format as the in-flight charts. The numbers survive the ticket leaving the board and its snapshots aging out.

## Today

Facts from `main` at `590c599`.

- The agent-gantt mod writes one snapshot per session to `.agent-team/gantt/<sessionId>.json` in the root checkout: `sessionId`, `cwd`, `updatedAt`, `total` (the session's cost from `session.usage()`, or null) and `rows`. Each row has `tokens` and `cost`. `task` rows repeat part of the main row's usage; `session` and `agent` rows don't overlap.
- `start.ts` deletes snapshot files older than a day each time the dashboard starts. `cleanSnapshot` in `api.ts` also ignores any snapshot not updated in the last day.
- `buildApi` matches a snapshot to a ticket with `ticketOf`: the longest worktree path that holds the snapshot's `cwd`, then that worktree's branch, matched to a ticket's state `branch` or to `feat/<prefix>-N`. It only accepts tickets on the board (`onBoard`).
- `server.ts` reads files under `.agent-team` only when every folder on the way is a real folder, and writes nothing. `api()` runs only when the page polls `/api`.
- `merged.ts` builds `MergedEntry` (`id`, `title`, `prUrl`, `issueUrl`, `mergedAt`) from `gh pr list`. `renderMerged` in `page/app.js` draws each one with no spend.

## Builds

1. **A spend ledger, `.agent-team/spend.json`, written by the dashboard server.** New module `agent-team/scripts/dashboard/spend.ts`.
   - Shape: `{ "sessions": { "<sessionId>": { "ticket": "CW-209", "cost": 0.42, "tokens": 955168, "updatedAt": 1762590000000 } } }`. Keyed by session, so a session seen again replaces its own entry and never counts twice.
   - A session's spend: `cost` is the snapshot's `total` (null when the snapshot has none); `tokens` is the sum of the `tokens` of its `session` and `agent` rows (`task` rows left out, since they repeat the main row).
   - `recordSpend(ledger, sessions)` takes the ledger and the snapshots matched to a ticket, and returns the new ledger. An entry is replaced only by a snapshot with a newer or equal `updatedAt`. The ledger keeps the newest 2000 sessions by `updatedAt` and drops the rest.
   - `spendByTicket(ledger)` returns `Record<ticketId, { cost: number | null; tokens: number }>`: the sum over that ticket's sessions. `cost` sums the sessions that have one, and is null only when none do.
   - `parseLedger(text)` reads the file and keeps only entries with a `ticket` like `<PREFIX>-<digits>`, finite non-negative `tokens` and `updatedAt`, and a `cost` that is a finite non-negative number or null. Bad JSON or a bad shape gives an empty ledger.
2. **Matching sessions to tickets for the ledger.** `ticketOf` gets a mode that accepts any ticket id from the branch, not only tickets on the board: the state ticket whose `branch` is the worktree's branch, else `feat/<prefix>-N`. That way the merge child's last minutes, after the ticket leaves the board, still count. The board match for the in-flight charts is unchanged.
3. **`server.ts` records in the background**, not only when the page polls.
   - At start and then every 30 seconds (a timer that does not keep Node alive, cleared by `close()`), it reads the snapshots and worktrees as `api()` does, matches them, and updates the ledger.
   - It writes `spend.json` only when the ledger changed: to a temp file in `.agent-team` opened with `wx`, then renamed over `spend.json`. It writes nothing when `.agent-team` is missing or is not a real folder, or when `spend.json` exists and is not a regular file. A failed write is skipped and tried again on the next round; it never stops `/api`.
   - At start it reads the existing `spend.json` with `readRegular`, so totals from earlier runs carry over.
4. **`/api` gives each merged entry its spend.** `MergedEntry` gets an optional `spend: { cost: number | null; tokens: number }`, set in `buildApi` from `spendByTicket` by the entry's `id`. No ledger entry for that id means no `spend` key.
5. **`renderMerged` shows it.** When `e.spend` is set, the row's `.sub` line gets `<span class="num cost">$0.42</span>` and `955.2k tokens`, using the page's existing `dollars` and `tokens`. A null cost shows the tokens only. No `spend` shows nothing extra, so a row looks as it does today.
6. **Tests**, per `AGENTS.md` § Testing.
   - `spend.test.ts`, one table-driven test for the ledger rules: a session counted once when seen twice, an older snapshot not replacing a newer entry, `task` rows left out of tokens, a ticket total summed over sessions, a null cost among known costs, all costs null, and bad file entries dropped.
   - `api.test.ts`: a merged entry gets its ticket's spend, a merged entry with no ledger data gets no `spend` key, and a session whose ticket is off the board is still matched for the ledger.
   - `server.test.ts`: the server writes `spend.json` from a snapshot without a page poll, and writes nothing when `.agent-team` is a link.
   - `app.test.js`: a merged row with spend shows the dollars and tokens; one without shows neither.

## Leaves out

- Spend for PRs merged before this ships. Their snapshots are mostly gone, and the ledger starts empty.
- A per-agent or per-session breakdown on the merged list.
- Any change to the agent-gantt mod or its snapshot format.
- Reading Claude Code transcripts (`agent_usage.py`) for spend.
- A total across all merged PRs.

## Calls I made

- **The dashboard server writes a new file, `.agent-team/spend.json`.** The server only read files until now. The ticket left the store to the build. I chose a ledger the server owns over two other places: `agent_usage.py --ticket` at merge time in `merge_pr.py` (more complete, since it reads every transcript, but it changes the merge script on the approval path, is slow, and its numbers wouldn't match the in-flight chart's), and adding the branch to the mod's snapshot and keeping snapshots longer (needs every machine to update the mod, and still loses data when `start.ts` prunes). The Chief of Staff's own write rule (only `state.json`) is unchanged: the server, not the Chief of Staff, writes the ledger.
- **Spend is only recorded while the dashboard runs.** A session that ran and aged past a day while the dashboard was down is never recorded. The Chief of Staff starts the dashboard at start-up and take-over, so this is the usual case covered. Recording every 30 seconds, not only on page polls, means a closed preview tab doesn't lose data.
- **The numbers are the gantt numbers.** Cost is each session's `total`, the same figure the chart header shows, summed over every session in the ticket's worktree (spec, build and merge children, with their subagents). Sessions in the root checkout, like the Chief of Staff's, are not charged to any ticket.
- **Keyed by session id, capped at 2000 sessions.** Replacing by session avoids double counting across polls. 2000 sessions is far more than the 200 merged PRs the list reads, and keeps the file small.
- **A null cost shows tokens only**, and a merged row with no ledger entry shows nothing, as the ticket asks. Neither shows `$0.00` or `–`.
- **The ledger matches any ticket id from the branch**, not only board tickets, so the merge child's work after the ticket leaves the board still counts.

## Touches

None of these: data, money, auth, user email, migrations. (Spend figures are API-equivalent cost estimates shown locally, not billing.)
