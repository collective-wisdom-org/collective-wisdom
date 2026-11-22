# WISE-492 plan: keep tab counts on one line

Spec: `docs/superpowers/specs/2026-11-22-wise-492-tab-counts-one-line-design.md` (approved).

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` (Node 24+).

## Task 1: CSS and scroll (`page/index.html`, `page/app.js`)

- `.tabs`: add `max-width:100%; overflow-x:auto;`.
- `.tabs button`: add `flex:none; white-space:nowrap;`.
- `selectTab`: for the selected tab when `focus` is false, call `tab.scrollIntoView({ block: 'nearest', inline: 'nearest' })`, guarded for non-browser test runs.
- No new tests (spec § Leaves out). Verify with the test command and a browser check at ~320px.
