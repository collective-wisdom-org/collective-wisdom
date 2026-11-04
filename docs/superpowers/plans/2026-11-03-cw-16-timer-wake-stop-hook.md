# Timer, wake and Stop-hook decision: Implementation Plan (CW-16)

Spec: [design](../specs/2026-11-03-cw-16-timer-wake-stop-hook-design.md)

## Tasks

1. `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Send or queue, a new short paragraph after the two bullets and "A queued relay stores the relay text only": add the sentence that reports `<PREFIX>-N: I may not hear when this run ends; say status to check.` under Moving when the ticket's `parentThreadId` isn't this thread. No other section, script or hook changes.
2. Post one comment on #16 with the five questions, each answer and its reason (the spec's § Decisions table). The answers rest on the user's relayed answers and `approve 16`.
3. Closeout (after the PR exists): as-built, spec Shipped, index rows, `docs/superpowers/release-notes/cw-16.md`.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- `git diff origin/main` touches only that new paragraph in § Send or queue in the skill, plus `docs/superpowers/`.
