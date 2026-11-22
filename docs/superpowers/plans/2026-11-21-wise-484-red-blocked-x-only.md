# WISE-484 plan: red blocked x only on dashboard cards

Spec: `docs/superpowers/specs/2026-11-21-wise-484-red-blocked-x-only-design.md` (approved). Build exactly that.

## Task 1: marks column (`agent-team/scripts/dashboard/page/app.js`, `page/index.html`, `page/app.test.js`)
In `marksColumn`, draw the blocked slot for any array `blockedBy`, empty when it has no entries; delete the `mark('clear', ...)` branch and fix the doc comment. Remove `.mark.clear` from `index.html`. In `app.test.js` replace the `green check` case with a `no open blocker` case and add a no-epic, no-blocker case, per spec § Change 3.
Verify: `node --test agent-team/scripts/dashboard/page/app.test.js`.

## Final
`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
