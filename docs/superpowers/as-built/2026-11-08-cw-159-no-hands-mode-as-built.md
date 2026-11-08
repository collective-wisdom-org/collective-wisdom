# As-built: No Hands mode

**Shipped:** in PR #215
**Ticket:** CW-159
**Spec:** [2026-11-08-cw-159-no-hands-mode-design.md](../specs/2026-11-08-cw-159-no-hands-mode-design.md)

## Differs from the spec

- Cost: the spec stops the run on any unknown ticket cost. A ticket for which `agent_usage.py --ticket` finds no sessions at all (exit 2 with `no transcripts`) counts as $0 only when it is gone from the state file (cancelled early) or in `spec` or `spec-queued` (just started). In any other stage, or merged, it is cost unknown (a Codex or Cursor child, or a moved projects dir, would otherwise switch the cost cap off). A cost that cannot be read any other way also gives `stop cost unknown`.
- Hands path: `pr_diff_delta.py` and `release_notes.py` are on it too, because `merge_pr.py` and `review_scope.py` import them (the import test found them).
- Start rules: `no_hands.py start` also needs `--thread` to equal `chiefThreadId`, needs the user's newest matching message to be exactly `no hands` (so `no hands off` and `no hands, and delete x` refuse), and after an ended run needs a `no hands` message newer than `endedAt`. `active()` re-checks that the start message is whole `no hands` and was sent no later than `startedAt`.
- Ticket cap: `check` computes `drain ticket-cap` from the setting; the Chief of Staff runs `no_hands.py drain ticket-cap` to record it. `cos_tick.py` drops `start-todo` only for a recorded drain and prints the `check` line each turn while a run is active; the model acts on `check` for cap and stop results. The Chief of Staff starts at most `cap - N` tickets per turn.
- `no hands off` ends in a drain that sets `paused` like other drains. `no hands` while `paused` is refused until `resume`.
- `no-hands` and `no hands off` are strict short-word commands in the user check. Added a short No Hands section to `README.md` and one sentence to `status.md`.
- Under a run, an unrated or non-string `status` counts as unrated and is auto-approved.
- Run record guard (code review pass 1): the `no-hands` op in `cos_state.py` allows only the moves `no_hands.py` makes (a fresh record when no run is active, a first `drain`, `endedAt` with `endReason` once), so a state edit cannot reopen an ended run, empty `started` or change `itemId`.
- Replay and stop (code review pass 2): a fresh record needs a new `itemId` and a `startedAt` later than the last `endedAt`; `active()` needs the item to be the user's newest exactly-`no hands` message sent at or before `startedAt`; a user `stop everything` after `startedAt` gives `check` `stop stopped-by-user`. Editing the state file by hand is out of scope: the record is only as trustworthy as the file.
- Linked worktrees: `no_hands.py` (`check`, `active()`) reads the root checkout's `.agent-team/state.json`, the first entry of `git worktree list`, so `approval_policy.py check no-hands` works from a child's worktree.
- Hands path, extra entries: the `owasp-security`, `agent-security` and `auditing-security` skills, `templates/machine-instruction.md`, `.claude/settings*.json`, `.cursor/hooks.json`, `.cursor/mcp.json`, `.mcp.json`, `.codex/`, `mods/`, `.claude/mods/`, `.claude/hooks/` and `.claude-plugin/`.
- `drain` and `end` refuse (exit 2) a reason with a word `cos_tick.SAFE` would not print into a plan line.
