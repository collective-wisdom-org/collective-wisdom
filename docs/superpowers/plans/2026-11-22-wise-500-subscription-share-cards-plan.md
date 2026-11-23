# WISE-500 plan: subscription share on dashboard cards

Spec: `docs/superpowers/specs/2026-11-22-wise-500-subscription-share-cards-design.md` (approved). Follow its `## Change` items 1 to 8 in order.

Tasks, each with its tests (AGENTS.md § Testing: one table per rule):

1. `agent-team/scripts/user_config.py`: `subscription <provider>` subcommand (+ docstring, usage line); table test in `test_user_config.py`.
2. `dashboard/spend.ts`: `claude` split on `SpendEntry`/`Spend`, `parseLedger` back-compat; extend `spend.test.ts`.
3. `dashboard/server.ts` + `dashboard/api.ts`: cached reader (`execFile python3 -I user_config.py subscription Claude`, 2 s timeout, 60 s cache), `Api.subscription`, passed through `buildApi`; extend `api.test.ts`/`server.test.ts` only for the pass-through and the null cases.
4. `dashboard/page/app.js`: `subscriptionShare`, merged card, `ganttSummary().claude`, `summaryLine(gantt, now, usage)`, the refresh loop, `renderMerged` trailing arg; extend `app.test.js`.

Verify: `python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
