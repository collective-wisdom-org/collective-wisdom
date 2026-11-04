# As-built: Chief of Staff stops restarting children that only wait on CI

**Shipped:** in PR #32
**Ticket:** none
**Spec:** [2026-11-03-cos-ci-wait-restarts-design.md](../specs/2026-11-03-cos-ci-wait-restarts-design.md)

## What shipped

- `agent-team/scripts/cos_idle_check.py`: `--wait <PREFIX>-N` mode (`check_wait` and helpers), on top of the CW-9 root convention. `--file` and the state file are untouched.
- `agent-team/scripts/test_cos_idle_check.py`: `test_wait_mode_tells_waiting_child_from_stalled`, eight rows.
- `agent-team/.claude/skills/chief-of-staff/SKILL.md`: the stuck check in § Full pass step 3, the intro and the Tools line.
- `agent-team/.claude/skills/ship-loop/SKILL.md`: § Run endings and § CI waits.
- `agent-team/docs/agents/chief-of-staff.md`: one "Done when" line.

## Differs from the spec

The spec matches what shipped. The one deliberate difference is from the app's version of the change: step 3 in the `chief-of-staff` SKILL.md keeps a reworded "Text about waiting is no exception: only a `waiting` line clears a finished run without a marker", where the source change deleted that sentence. Exit 2 and a child's own "waiting on CI" text must still not clear a run.

## Verification

`python3 -I -m pytest -q agent-team/scripts` passes (335 tests, 327 before). IHAG's own test file passes against the shipped script. `shellcheck install.sh agent-team/scripts/*.sh` is clean.
