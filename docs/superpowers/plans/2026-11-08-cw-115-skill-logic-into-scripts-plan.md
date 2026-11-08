# CW-115 plan: move skill logic into scripts

Spec: `docs/superpowers/specs/2026-11-08-cw-115-skill-logic-into-scripts-design.md`. Files are under `agent-team/`.

1. `scripts/review_gate.py` + `test_review_gate.py`; cut `ship-loop/SKILL.md` § Phases 4 pre-`MERGE READY` paragraph; move `merge-pr` § Pre-merge checks list into the `merge_pr.py` docstring and cut the skill.
2. `scripts/cos_head_check.py` + `test_cos_head_check.py`; cut `chief-of-staff/SKILL.md` § Send or queue head check paragraph and the `approve N` on `awaiting-review` wording in § Commands.
3. `scripts/pm_hygiene.py` (`fill`, `drift`, `stale`) + `test_pm_hygiene.py`; cut `project-manager/SKILL.md` § Cleanup and § Stale tickets.
4. `cos_rank.py dry` + new rows in `test_cos_rank.py`; cut § Backlog pick step 4.
5. Measure sizes (`wc -c`), run the suite and shellcheck, record before and after in the PR.

Tasks 1+5, 2 and 3+4 touch disjoint files and run in parallel.
