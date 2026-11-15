# CW-411 plan: Reorder the dashboard tabs and add a Backlog tab count

**Spec:** [2026-11-15-cw-411-reorder-tabs-backlog-count-design.md](../specs/2026-11-15-cw-411-reorder-tabs-backlog-count-design.md)

Files: `agent-team/scripts/dashboard/page/index.html`, `app.js`, `app.test.js`.

## Task 0: test

In `app.test.js`, add `backlog` to every expected result of the `tab counts` test (`backlog: 9` for the sample, `0` for the empty and `undefined` rows) and add one row with a `Backlog` group whose `count` is not a number (`backlog: 0`). Run `node --test agent-team/scripts/dashboard/page/app.test.js`; it fails.

## Task 1: code

1. `app.js`: `tabCounts` returns `backlog` (the `BACKLOG` group's `count` as a number, 0 when missing or not a number); update its doc comment. `TAB_LABELS` gains `backlog: 'Backlog'`.
2. `index.html`: order the tab buttons Ship loop, Backlog, Done, Chief of Staff; order the panels the same; add `<span class="pill tab-count" data-count="backlog" aria-hidden="true"></span>` after `Backlog` in its button.

## Verify

`python3 -I -m pytest -q agent-team/scripts` and the dashboard node test command from `AGENTS.md`.
