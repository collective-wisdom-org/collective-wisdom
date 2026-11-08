# CW-213: Show the agent gantt on merged PRs in the dashboard

**Status:** Shipped
**Shipped:** in PR #214, as specified
**Ticket:** [#213](https://github.com/collective-wisdom-org/collective-wisdom/issues/213)
**Related:** #209 (PR #211) added the spend ledger this follows.

## Goal

A merged PR row in the dashboard has the same collapsible "Agents" chart a ticket card has, so you can see after the merge which agents ran on the ticket, when, and what each cost. The chart survives a dashboard restart and the ticket's worktree being removed.

## Today

Facts from `main` at `23b0002`.

- `buildApi` in `agent-team/scripts/dashboard/api.ts` cleans each live snapshot with `cleanSnapshot` and attaches it as `gantt` to the board row its worktree branch matches (`ticketOf` with `onBoard`). A merged ticket is off the board, so nothing gets attached to its `MergedEntry`.
- `cleanSnapshot` drops a snapshot whose `cwd` is not a worktree or that was not updated in the last day. `start.ts` deletes snapshot files older than a day. `readSnapshots` in `server.ts` reads `.agent-team/gantt/*.json`.
- `server.ts` runs `recordRound` at start and every 30 seconds: `ledgerSessions` matches live snapshots to any ticket id from the branch, `recordSpend` folds them into the ledger, and `writeSpend` writes `.agent-team/spend.json` through a `wx` temp file and a rename, only when it changed and only into a real `.agent-team` folder. The ledger keeps per-session totals, not rows.
- `page/app.js`: `ticket()` draws a board row's `<details class="chart" data-ticket=…>` with an `Agents <pill>` summary and an empty `.chart-body`; `draw()` fills every `.chart-body` each second with `renderGantt(row.gantt, now)`. `renderMerged` draws merged rows with no chart. `drawMerged` rewrites the merged list only when its html changed.

## Builds

1. **A gantt history, `.agent-team/gantt-history.json`, written by the dashboard server.** New module `agent-team/scripts/dashboard/history.ts`, beside `spend.ts`.
   - Shape: `{ "sessions": { "<sessionId>": { "ticket": "CW-213", "session": <Session> } } }`, where `Session` is what `cleanSnapshot` returns (`sessionId`, `cwd`, `updatedAt`, `stale`, `total`, `rows`).
   - `recordHistory(history, matched)` takes the same `{ ticket, session }[]` that `ledgerSessions` already returns. A session replaces its own entry only when its `updatedAt` is newer or equal. The newest 500 sessions by `updatedAt` stay.
   - `historyByTicket(history)` returns `Record<ticketId, Session[]>`, oldest `updatedAt` first, as the board charts sort. Each stored session comes back finished: `stale: false`, and every open row and segment closed at the session's `updatedAt`, so a merged chart never shows a running bar.
   - `parseHistory(text)` keeps only entries with a ticket like `<PREFIX>-<digits>`, a string `sessionId` equal to the key, a string `cwd`, a finite non-negative `updatedAt`, and a `rows` array. Rows go through the same cleaning `cleanSnapshot` uses (name, label and segment caps), so a hand-edited file can't feed the page anything a live snapshot couldn't. Bad JSON or a bad shape gives an empty history, as `parseLedger` does.
2. **`server.ts` records the history in the same round as the ledger.** `recordRound` passes the matched sessions to both `recordSpend` and `recordHistory`. The temp-file-and-rename write in `writeSpend` takes the file name as an argument and writes `gantt-history.json` under the same rules: only when it changed, only into a real `.agent-team` folder, never over a link, a failed write retried next round and never stopping `/api`. At start the server reads the existing `gantt-history.json` with `readRegular`.
3. **`/api` gives each merged entry its sessions.** `MergedEntry` gets an optional `gantt: Session[]`, set in `buildApi` from `historyByTicket` by the entry's `id`. A ticket with no stored sessions gets no `gantt` key. Board rows are unchanged.
4. **`renderMerged` draws the chart.** A merged row with a non-empty `gantt` gets the same `<details class="chart">` the cards have, with `data-merged="<id>"` instead of `data-ticket` so a ticket id on both lists can't fill the wrong body. A row without one shows no section, so it looks as it does today. `renderMerged` takes the set of open merged charts and keeps them open when the list is redrawn; `drawMerged` collects that set from the page first, as `poll` does for the cards. `draw()` fills each merged `.chart-body` from `last.merged` with `renderGantt`. The chart itself is unchanged.
5. **Tests**, per `AGENTS.md` § Testing.
   - `history.test.ts`, one table-driven test for the history rules: a session seen twice is stored once, an older snapshot doesn't replace a newer entry, the cap keeps the newest, sessions come back per ticket oldest first and closed (no open row or segment, `stale` false), and bad file entries or bad JSON give an empty or smaller history.
   - `api.test.ts`: a merged entry gets its ticket's sessions; one with none gets no `gantt` key.
   - `server.test.ts`, added to the CW-209 background test: the server writes `gantt-history.json` from a snapshot without a page poll, writes nothing through a link, and after the snapshot file is deleted and the server restarts, the stored session is still in the file. (The merged list comes from `gh`, which the server test doesn't fake; the `/api` side is covered in `api.test.ts`.)
   - `app.test.js`: a merged row with sessions has an `Agents` section with the session count; one without has none; an open merged chart stays open across a redraw.

## Leaves out

- Gantt for PRs merged before this ships, or merged while the dashboard wasn't running: the history starts empty and records only while the server runs.
- Any change to `renderGantt`, the agent-gantt mod, its snapshot format, `start.ts` pruning, or the spend figures.
- A separate endpoint that loads a merged chart only when it opens.

## Calls I made

- **The /api response carries the merged charts inline, every 5-second poll.** The ticket asks for the same chart drawn the same way, and a lazy endpoint adds a second fetch path for the page. The 500-session cap bounds the payload; on a busy repo it can still be a few megabytes a poll, on localhost. If that turns out to be too slow, a follow-up can load a chart only when it opens.
- **A second file, `gantt-history.json`, not more fields in `spend.json`.** The ledger's contract and its 2000-session cap stay as they are, and a bad rows field can't cost a ticket its spend figure. Both files are written by the same round with the same safe write.
- **500 sessions, not 2000.** Rows are much bigger than spend totals. 500 sessions covers roughly the last hundred merged tickets at a few sessions each; older merged rows lose their chart first and then show no section, as a row with no recorded sessions does.
- **Stored sessions are shown finished.** A session still open at its last snapshot (for example the merge child, recorded within 30 seconds of the merge) is closed at its last update rather than drawn as running.
- **Matching is the spend ledger's.** The history uses `ledgerSessions`, so it covers the same sessions the spend figure sums: every worktree session whose branch names the ticket, including the merge child after the ticket leaves the board. Root checkout sessions (the Chief of Staff) belong to no ticket.

## Touches

None of these: data, money, auth, user email, migrations. The server writes one more local file under `.agent-team`.
