# CW-350 plan: Done tab

Spec: `docs/superpowers/specs/2026-11-14-cw-350-dashboard-done-tab-design.md`

## Task 1: markup in `agent-team/scripts/dashboard/page/index.html`

1. Add the `tab-done` button (`data-tab="done"`, `aria-controls="panel-done"`, `tabindex="-1"`, text `Done`) after the Chief of Staff button.
2. Remove `<h2>Done</h2>` and `<div id="merged">...</div>` from `panel-ship`.
3. After `panel-cos`, add `<div id="panel-done" role="tabpanel" aria-labelledby="tab-done" hidden>` holding `<div id="merged"><p class="quiet">Loading</p></div>`.

## Task 2: `tabFromStorage` in `app.js` and its test

1. Return `value` when it is exactly `'cos'` or `'done'`, else `'ship'`.
2. In `app.test.js`, extend the `tabFromStorage` table with `'done'` → `'done'` and `'DONE'` → `'ship'`.

## Task 3: README

In `README.md` § Dashboard, say the Done list is on the Done tab (not "below the cards") and that the page has three tabs, Ship loop, Chief of Staff and Done.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, and `git diff` shows only these edits.
