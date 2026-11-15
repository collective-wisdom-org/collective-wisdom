# CW-355 plan: drop left-Todo tickets from the dashboard lists

Spec: `docs/superpowers/specs/2026-11-14-cw-355-todo-list-stale-design.md` (approved). Build to the spec; keep tests within AGENTS.md § Testing.

## Task 1: remove entries on start, merged, drop (Python)

- `agent-team/scripts/cos_lists.py`: add `remove(ids, file=None)` per the spec (both kinds, keep `at`, same safety checks and temp-file write as `save`, no write when nothing matches or the file is absent, raises `Cannot` on a failed write). Update the docstring.
- `agent-team/scripts/cos_state.py`: in `apply_file`, after the ops apply (also when the result is `unchanged`), collect ids from `start`, `merged`, `drop` ops and call `cos_lists.remove` on `tracker-lists.json` in the state file's folder. Swallow every exception; output and exit code unchanged. Update the docstring. Mind the import cycle (`cos_lists` imports `app_root` only).
- Test: one table-driven test in `test_cos_state.py` per the spec (three ops, plus a bad-file row where apply still prints the usual output and exits 0).
- Run: `python3 -I -m pytest -q agent-team/scripts`.

## Task 2: age line (TS + page)

- `dashboard/lists.ts`: keep each kind's `at` (ms or null); give each item a `readAt`.
- `dashboard/api.ts`: add `readAt` and `stale` (over 1 hour) to the Todo and Backlog groups for the file path only.
- `dashboard/page/app.js` (+ `index.html` css if needed): a stale group shows `Read from the tracker <age> ago` (same duration words as the `waiting` counter) and greys its rows; fresh or no `readAt` shows nothing.
- Tests: one table test for the age in `lists.test.ts`/`api.test.ts`; one in `app.test.js`.
- Run: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.

## Task 3: docs

- `chief-of-staff/SKILL.md` (lines naming `cos_lists.py` and `cos_todo.py`) and `agent-team/docs/agents/org-chart.md`: also name `cos_state.py apply` as a caller. Mark the spec `Status: Shipped` / `**Shipped:** in PR #N` at open-pr closeout, not now.
