# CW-213 plan: show the agent gantt on merged PRs in the dashboard

Spec: `docs/superpowers/specs/2026-11-08-cw-213-merged-pr-gantt-design.md`. Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

1. `agent-team/scripts/dashboard/api.ts`: export `cleanRow` (the row cleaning `cleanSnapshot` uses). `buildApi` takes `history` (`Record<string, Session[]>`, default `{}`) and sets `gantt` on a merged entry only when its id has a non-empty list. Board rows are unchanged.
2. `agent-team/scripts/dashboard/merged.ts`: `MergedEntry` gets optional `gantt: Session[]`.
3. `agent-team/scripts/dashboard/history.ts` (new, beside `spend.ts`): `parseHistory`, `recordHistory`, `historyByTicket`.
   - Shape `{ sessions: { [sessionId]: { ticket, session } } }`.
   - `parseHistory` keeps entries with a ticket matching `^[A-Za-z][A-Za-z0-9]*-\d+$`, a `session.sessionId` string equal to the key, a string `cwd`, a finite non-negative `updatedAt`, and a `rows` array. Rows go through `cleanRow(r, null)`. Bad JSON or shape gives an empty history.
   - `recordHistory(history, matched)`: a session replaces its entry when its `updatedAt` is newer or equal (skip sessions with no `sessionId`); the newest 500 by `updatedAt` stay.
   - `historyByTicket(history)`: per ticket, sessions oldest `updatedAt` first, each with `stale: false` and every open row end and open segment end set to the session's `updatedAt` (segment end `Math.max(start, updatedAt)`).
4. `agent-team/scripts/dashboard/server.ts`: `writeSpend` becomes `writeJson(agentDir, name, text)` with the same rules (temp file `wx` + rename, real `.agent-team` folder, target absent or regular file, failed write cleaned up). Read `gantt-history.json` at start with `readRegular`. `recordRound` passes the matched sessions to `recordSpend` and `recordHistory`, writes each file only when its JSON changed (a failed write is retried next round), and a failure in one never stops the other or `/api`. `api()` passes `history: historyByTicket(history)` to `buildApi`.
5. `agent-team/scripts/dashboard/page/app.js`: `renderMerged(list, page, size, open)` takes the set of open merged chart ids (default empty set) and, for a row with non-empty `gantt`, adds `<details class="chart" data-merged="<id>"[ open]><summary>Agents <span class="pill">N</span></summary><div class="chart-body" data-merged="<id>"></div></details>`. `draw()` fills each `.chart-body[data-merged]` from `last.merged` with `renderGantt` (the existing `data-ticket` lookup must not touch merged bodies). `drawMerged` collects open merged chart ids from `details.chart[data-merged][open]` before redrawing, and the html-changed check must include session ids so a new session redraws the list (use a key that maps `gantt` to session ids, as `poll` does for the status).
6. Tests:
   - `history.test.ts`: one table for the history rules (session stored once, older snapshot doesn't replace newer, cap keeps newest, per-ticket oldest first and closed with `stale` false and no open row or segment, bad entries or bad JSON give empty or smaller history).
   - `api.test.ts`: a merged entry gets its ticket's sessions; one with none has no `gantt` key.
   - `server.test.ts`: extend the CW-209 background test: `gantt-history.json` is written from a snapshot without a page poll, nothing is written through a link, and after the snapshot is deleted and the server restarts the stored session is still in the file.
   - `page/app.test.js`: merged row with sessions has an `Agents` section with the count; one without has none; an open merged chart stays open across a redraw.
7. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
