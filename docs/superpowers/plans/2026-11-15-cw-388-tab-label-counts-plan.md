# CW-388 plan: ticket counts in the Ship loop and Done tab labels

Spec: `docs/superpowers/specs/2026-11-15-cw-388-tab-label-counts-design.md`

## Task 1: `agent-team/scripts/dashboard/page/`

1. `app.js`: pull the band sum out of `renderBadges` into `bandSum`; export `tabCounts(status, merged)`; add `drawTabCounts()` beside `drawStatus` and call it in `poll()` after `drawCos()`.
2. `index.html`: add the empty `.pill.tab-count` spans to the Ship loop and Done tabs and the `.tabs .pill` rule.
3. `app.test.js`: one table-driven `tabCounts` test (all bands, empty lists, undefined).

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
