# CW-51 plan: trust the state file

Spec: [2026-11-03-cw-51-trust-state-file-design.md](../specs/2026-11-03-cw-51-trust-state-file-design.md). Edit under `agent-team/` only.

1. `agent-team/scripts/cos_state.py`: `retire` takes optional `successor` and stores it; `show` prints retired entries as `<id>><successor>` (`<id>>?` without); `start` requires `parentThreadId`; update the docstring. Table-driven tests in `test_cos.py` (retire with/without successor, re-retire keeps the first entry, `show` retired line, `start` without `parentThreadId` rejects). Fix any existing tests that call `start` without it.
2. `agent-team/scripts/cos_parent_check.py`: docstring only (drop the "any local agent" clause).
3. `agent-team/docs/agents/chief-of-staff.md`: add the "What it trusts" section.
4. `agent-team/.claude/skills/chief-of-staff/SKILL.md`: intro (retirement from state, `successor`, Moved-to only as legacy fallback, link to role doc), drop the `parentThreadId` backfill (State file, Full pass step 1, take-over 4.1) and the Archiving re-read, simplify "Deleting the wake" and Start-up clean-up step 1, handoff step 5 passes `successor`, tidy "Moved-to check" and "Other thread reads". Continuation child section keeps its read and worktree check.
5. `reference.md`: Resume mode, Retired thread, Failed handoff, rebuild per the spec.
6. Check: `grep -rn "any local agent\|state can be edited\|proves nothing" agent-team/` is empty; `python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh agent-team/scripts/*.sh`.
