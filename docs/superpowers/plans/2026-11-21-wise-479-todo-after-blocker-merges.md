# WISE-479 plan: Mark tickets Todo when their last blocker merges

Spec: `docs/superpowers/specs/2026-11-21-wise-479-todo-after-blocker-merges-design.md` (approved).

## Task 1: `cos_unblocked.py` and its test (Task 0 is the test)

- Write `agent-team/scripts/test_cos_unblocked.py`: one table-driven test through `main()` with stdin (style of `test_cos_todo.py`), rows exactly as in the spec § Test, plus one bad-stdin row (exit 2, `unblocked: cannot ...`).
- Write `agent-team/scripts/cos_unblocked.py` per spec § Change 1. Import `cos_todo.blockers`, `cos_todo.is_open`, `pm_hygiene.state_of`, `pm_hygiene.labels_of`. Match the merged ticket by id, or by number alone when a blocker is a bare number or an object with only `number`. Lines in id order; ends `unblocked: <C> checked, <T> to Todo`.
- Verify: `python3 -I -m pytest -q agent-team/scripts/test_cos_unblocked.py`, then the full `python3 -I -m pytest -q agent-team/scripts`.

## Task 2: Chief of Staff text and docs

Spec § Change 2, 3 and 4: `readiness.md` new § Unblocked after a merge and the § Todo start wording; `SKILL.md` `MERGED #N` bullet and reading-table row; `sweep.md` § Merged check `merged` line; `report-format.md` example Moving line; `org-chart.md` Chief of Staff row. Plain sentences, no em dashes. Verify with the full pytest suite (test_agent_files.py, test_call_sites.py).

## Commit

`feat: mark tickets Todo when their last blocker merges (WISE-479)`, push the branch only.
