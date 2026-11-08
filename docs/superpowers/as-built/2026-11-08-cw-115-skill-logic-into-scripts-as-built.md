# As-built: Move more skill logic into scripts

**Shipped:** in PR #190
**Ticket:** CW-115
**Spec:** [2026-11-08-cw-115-skill-logic-into-scripts-design.md](../specs/2026-11-08-cw-115-skill-logic-into-scripts-design.md)

## Differs from the spec

- Size targets: the spec asked for ship-loop -900, project-manager -2000 and the four files together -4500 bytes. Shipped: ship-loop -714, project-manager -1248, total -4180. Chief of Staff (-1004) and merge-pr (-1214) met their targets.
- `review_gate.py` names only the stale or failing review in `rerun`, not both. Reviews posted on different heads still give `rerun both`. A head resolved for conflicts with `Review after conflict resolution` `off` prints `pass`, as the merge gate accepts it. A failed diff compare prints `rerun`, not exit 2. `--help` prints the usage and exits 0.
- `cos_head_check.py`: a failed setting read counts as `on` (`conflict withdraw`), because `project_config.review_after_conflict()` never reports a failure.
- The Chief of Staff's `BLOCKED:` handling for a merge child now runs `cos_head_check.py`. When the stored head differs from the live head it prints the moved-head relay, where the old text sent the conflict relay with the approval whatever the head.
- `pm_hygiene.py`: `drift` skips PRs whose ticket is in the Chief of Staff's `tickets`. `stale` prints and compares a date (`since YYYY-MM-DD`), and the skill saves the date in `pm.flaggedStale`. `fill` and `stale` accept two `list-tickets` results pasted back to back.
- `cos_rank.py dry` has no `dry: stop` line; with a well-formed `rankedAt` the Backlog check is always possible.
