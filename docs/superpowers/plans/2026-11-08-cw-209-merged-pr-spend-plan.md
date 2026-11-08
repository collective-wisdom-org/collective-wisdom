# CW-209 plan: show agent spend on merged PRs in the dashboard

Spec: `docs/superpowers/specs/2026-11-08-cw-209-merged-pr-spend-design.md`. Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

1. `agent-team/scripts/dashboard/spend.ts`: `parseLedger`, `recordSpend` and `spendByTicket`. Keyed by session id, tokens from `session` and `agent` rows only, newest 2000 sessions kept.
2. `agent-team/scripts/dashboard/api.ts`: `ticketOf` gets a mode that accepts any ticket id from the branch, and `ledgerSessions` returns the sessions matched that way. `buildApi` takes `spend` (default `{}`) and sets `MergedEntry.spend` only for ids in it. `merged.ts` gets the optional field.
3. `agent-team/scripts/dashboard/server.ts`: read `spend.json` at start; record at start and every 30 seconds (unref'd timer, cleared in `close()`); write only when changed, through a temp file opened with `wx` and a rename, and not when `.agent-team` is not a real folder or `spend.json` is not a regular file. Share the snapshot reading with `api()`.
4. `agent-team/scripts/dashboard/page/app.js`: `renderMerged` adds the cost and tokens to the `.sub` line when `spend` is set.
5. Tests: `spend.test.ts` (one table), additions to `api.test.ts`, `server.test.ts` and `page/app.test.js`.
6. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
