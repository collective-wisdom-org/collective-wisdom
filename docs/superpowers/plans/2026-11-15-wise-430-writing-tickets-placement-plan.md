# WISE-430 plan: Writing tickets on the Backlog tab

Spec: `docs/superpowers/specs/2026-11-15-wise-430-writing-tickets-placement-design.md`

Task 0 (tests first, then code), one task:

1. `mods/agent-gantt/hooks/snapshot.ts` + `snapshot.test.ts`: `pickRequest` prefers a `Writing ticket:` line above the request marker. Bump `plugin.json` to 0.1.14.
2. `page/app.js` + `app.test.js`: drop `Writing tickets` from the In progress band, `tabCounts.ship` and the header counts; `renderBacklog` draws it first.
3. `ticket-helper.md`: new `Writing ticket:` template line and new thread title.
4. `README.md`, `docs/compatibility.md`: one-sentence updates.

Verify: `python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
