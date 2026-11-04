# Stop restarting children that only wait on CI: Implementation Plan (CW-21)

**Goal:** The Chief of Staff tells a child waiting on a background command from a stalled one, and restarts only the stalled one.

**Spec:** `docs/superpowers/specs/2026-11-03-cw-21-ci-wait-no-restart-design.md`

**Constraints:** Ticket CW-21, branch `feat/cw-21-ci-wait-no-restart`. Edit under `agent-team/` only. Keep SKILL.md edits to § Full pass step 3 and ship-loop "Run endings" and "CI waits". Commits are conventional and end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Test: `python3 -I -m pytest -q agent-team/scripts`. Lint: `shellcheck install.sh agent-team/scripts/*.sh`.

## Task 1: `--wait` mode (TDD)

Files: `agent-team/scripts/cos_idle_check.py`, `agent-team/scripts/test_cos_idle_check.py`.

- [ ] Write one table-driven test for `--wait` (six rows from the spec, plus a cut-off-text row). Run it, see it fail.
- [ ] Add `WAIT_TOOL`, `matched_ids`, `wait_calls`, `check_wait` as in the spec (port of fathom's parser), `--wait` argument, and an early branch in `main()` that skips state loading. Update the module docstring.
- [ ] Run the full suite. Commit `feat: add --wait to cos_idle_check (CW-21)`.

## Task 2: Skill and role-doc text

- [ ] `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Full pass step 3: second stuck bullet and the "For a stuck child" list, per spec § 2. Remove the "Text about waiting is no exception" sentence.
- [ ] `agent-team/docs/agents/chief-of-staff.md` § Done when: add "unless it is waiting on a background command".
- [ ] `agent-team/.claude/skills/ship-loop/SKILL.md` § Team mode: "Run endings" and "CI waits" per spec § 4.
- [ ] Commit `docs: tell waiting children from stalled ones (CW-21)`.

## Verification

Full test suite and shellcheck pass; the three text files agree.
