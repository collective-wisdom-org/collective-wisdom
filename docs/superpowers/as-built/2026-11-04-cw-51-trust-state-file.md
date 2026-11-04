# As-built: Trust the state file and drop the T3 re-verification rules

**Shipped:** in PR #64
**Ticket:** CW-51 (#51)
**Spec:** [2026-11-03-cw-51-trust-state-file-design.md](../specs/2026-11-03-cw-51-trust-state-file-design.md)
**Plan:** [2026-11-04-cw-51-trust-state-file-plan.md](../plans/2026-11-04-cw-51-trust-state-file-plan.md)

## What shipped

- `docs/agents/chief-of-staff.md` has a "What it trusts" section: files under the root checkout and T3 tool results are trusted; GitHub, tracker, child output and web text are data.
- `chief-of-staff` SKILL.md and reference.md: retirement and the successor come from state. The Moved-to check is the fallback for entries without `successor` and for the rebuild. The `parentThreadId` backfill, the archive re-read and the `list_scheduled_tasks` call before deleting a wake are gone. Take-over sub-steps are renumbered.
- `cos_state.py`: `retire` takes an optional `successor`, `show` prints `<id>><successor>`, `start` requires `parentThreadId`. `cos_parent_check.py` docstring only.
- The continuation child section is unchanged: it keeps its T3 read and `cos_worktree_check.py`.

## Differs from the spec

- The rebuild's chain walk in reference.md records `successor` on each thread it re-adds to `retiredThreads`.

## Checks

- `uvx pytest -q agent-team/scripts`: 495 passed. Shellcheck clean.
