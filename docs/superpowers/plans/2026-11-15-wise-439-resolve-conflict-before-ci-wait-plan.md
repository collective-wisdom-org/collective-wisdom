# WISE-439 plan: resolve a conflict before the CI wait

**Spec:** [2026-11-15-wise-439-resolve-conflict-before-ci-wait-design.md](../specs/2026-11-15-wise-439-resolve-conflict-before-ci-wait-design.md)

Work in the feature worktree. Tests per `AGENTS.md` § Testing: one table-driven test per rule. Run `python3 -I -m pytest -q agent-team/scripts` (or `uvx pytest`) and `shellcheck agent-team/scripts/*.sh` after each task.

## Task 1: `project_config.py target` and `wait-for-ci.sh` conflict line

- Add a `target` subcommand to `agent-team/scripts/project_config.py` printing `target_branch()`.
- In `wait-for-ci.sh`, on each poll try with no check rows, read `gh.sh pr view <N> --json mergeable,mergeStateStatus`. `CONFLICTING` or `DIRTY`: print `wait-for-ci: PR #N at <sha>: conflict with <target>`, exit 3. `UNKNOWN`, other values or a failed read keep polling. This runs before the `no CI declared` exit 0.
- The `no checks` line becomes `wait-for-ci: no checks on PR #N at <sha> (mergeable <M>, mergeStateStatus <S>)`, `unknown` when unread. Exit 2. Update the usage comment (exit 3).
- Extend `test_wait_for_ci.py` (one table): no checks + CONFLICTING ends with the conflict line, exit 3, no 20-poll loop (count sleeps); + MERGEABLE keeps the poll and `no checks`; + UNKNOWN polls on; no CI declared + CONFLICTING gives the conflict line.

## Task 2: state field, ready check, sweep

- `cos_state.py`: ticket field `conflictHead` (full 40-hex SHA or null, any stage), documented in the docstring like `changesRelayed`; add to `TICKET`. Add a case to the existing field-validation table in `test_cos_state.py`.
- `cos_ready_check.py`: add `mergeable,mergeStateStatus,statusCheckRollup` to the one `pr list` call. In `build_line` (agents mode and ci mode), before the ready/building test: `CONFLICTING` or `DIRTY` with an empty rollup prints `conflict <tid> #PR head <short>` and flags `(tid, "conflict")`, unless `info["conflictHead"]` equals the PR's full head (then `building <tid> #PR (conflict relayed)`). Update the docstring. `check()` flagged reasons gain `conflict`.
- `cos_sweep.py`: add `conflict` to ACTION["ready"] and the docstring.
- Table-driven test in `test_cos_ready_check.py`: CONFLICTING + empty rollup flagged; DIRTY alone flagged; MERGEABLE no checks not; CONFLICTING with checks not; CONFLICTING with conflictHead == head not. Add one sweep case if cheap.

## Task 3: skills

- `ship-loop/SKILL.md` § CI waits: the `conflict with <target>` line (exit 3), what the child does, third conflict line in one run is `BLOCKED:`, and the time-limit decision (no new cap; two runs stay the cap; `BLOCKED:` quotes the `no checks` line with PR state). Fix the list "`cannot read`, `no checks` or `cannot watch`".
- `open-pr/SKILL.md`: Primary loop step 2 goes back to step 1 on the conflict line; one sentence at the top of § Conflict resolution for a child that has not reported `MERGE READY`.
- `chief-of-staff/sweep.md` § Sweep: bullet for the ready check's `conflict` line.
- `chief-of-staff/SKILL.md` § Child path: the **Conflict** step per spec § 5; also add `conflict` to the ready-check wording where lines are listed (SKILL.md/sweep.md mentions of `ready`, `pushed`).
- Search `agent-team/` for other places listing the ready check's lines or `wait-for-ci.sh` exit codes and update them.
