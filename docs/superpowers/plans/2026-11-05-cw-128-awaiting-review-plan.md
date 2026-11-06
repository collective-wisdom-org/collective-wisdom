# CW-128 awaiting-review: build plan

Spec: `docs/superpowers/specs/2026-11-05-cw-128-awaiting-review-design.md` (approved at commit 7daee7e). This plan only says what moved since the spec and how the work splits.

## What moved since the spec

CW-127 (#136) and #140 are on `main`. The rule in `agent-team/scripts/merge_pr.py` is not the pair of helpers the spec named:

- `required_reviews(f)` returns the stop line for `reviewDecision == REVIEW_REQUIRED`, or `None`. It returns `None` and sets `f["bypass"]` when the signed-in login is a codeowner (#140).
- `teammate_approval(f)` returns the stop line for the `Require teammate approval` rule. It only counts reviews whose `authorAssociation` is `OWNER`, `MEMBER` or `COLLABORATOR`, and ignores the author's own.
- `gate()` loops over both. `f` is the facts dict from `read_facts`.

Decisions for the build:

- Task 1 extracts, without changing any behaviour or any expectation in `test_merge_pr.py`: `latest_verdicts(f)` (the per-reviewer latest verdict map that `teammate_approval` builds), `requested_names(f)` (the names list inside `required_reviews`), and `review_stop(f)` (first non-`None` of `required_reviews`, `teammate_approval`). `gate()` calls `review_stop`.
- `cos_review_check.py` builds the same facts dict (`login` from `gh api user`, `codeowners` from `merge_pr.codeowners`, `teammate` from `project_config.setting`, `pr`, plus the `gh pr view` fields) and calls `review_stop(f)`. The merge gate and the stage check cannot drift apart.
- Because of #140, when the Chief of Staff's gh login is a codeowner, `REVIEW_REQUIRED` alone does not hold a ticket in `awaiting-review` (the merge gate lets that login past it). The teammate rule with the row `on` still does. This follows the merged gate and is stated in the script's docstring.
- `changes` (no-argument check): `reviewDecision == CHANGES_REQUESTED`, or the row is `on` and `latest_verdicts` has a `CHANGES_REQUESTED` entry. `approved`: `review_stop(f)` is `None`; the logins are the `APPROVED` entries on the head from `latest_verdicts` when the row is `on`, else `github`.

## Tasks

1. **merge_pr.py refactor** (above). Run `test_merge_pr.py` unchanged.
2. **cos_state.py**: `awaiting-review` stage, `STAMPED` membership, the `awaiting-review` to `awaiting-merge` same-head keeps `lastSeenAt` exception, `heldApproval` key and its rules, `show` counts line, docstring. New `test_cos_state.py`, one table.
3. **cos_review_check.py** with `--route` and the no-argument check, `--prs FILE` for tests. New `test_cos_review_check.py`, two tables.
4. **cos_merged_check.py** `WAITING` gains the stage (one test row). **cos_sweep.py** review part and last-line tail (one test row).
5. **Docs**: chief-of-staff `SKILL.md` (Lanes, State file stages, Full pass `MERGE READY`, Sweep, Commands, Send or queue table), `approvals.md` (`awaiting-review` block differences), `state-keys.md` (`heldApproval`, cut-off note), `status.md` (group), `startup.md` (rebuild), `ship-loop` Team mode Relays bullet, `docs/agents/org-chart.md` chart node.

Tasks 1 to 4 are code and tests; task 5 is markdown only. They touch different files.

## Overlap

Merged since the spec: #131 (team mode only) and #136, #140. Still open: #132, CW-60, CW-72, CW-133. Merge `origin/main` in before `MERGE READY`, keep both sides, and run the full suite.
