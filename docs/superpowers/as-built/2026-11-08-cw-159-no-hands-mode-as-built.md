# As-built: No Hands mode

**Shipped:** in PR #215
**Ticket:** CW-159
**Spec:** [2026-11-08-cw-159-no-hands-mode-design.md](../specs/2026-11-08-cw-159-no-hands-mode-design.md)

## Differs from the spec

- Cost: the spec stops the run on any unknown ticket cost. A just-started ticket has no session yet, so the newest ticket in `started` may be unmeasured and counts as $0; an earlier unknown still gives `stop cost unknown`.
- Hands path: `pr_diff_delta.py` and `release_notes.py` are on it too, because `merge_pr.py` and `review_scope.py` import them (the import test found them).
- Start rules: `no_hands.py start` also needs `--thread` to equal `chiefThreadId`, refuses when the newest matching message is `no hands off`, and after an ended run needs a `no hands` message newer than `endedAt`.
- Ticket cap: `check` computes `drain ticket-cap` from the setting; the Chief of Staff runs `no_hands.py drain ticket-cap` to record it. `cos_tick.py` drops `start-todo` only for a recorded drain and prints the `check` line each turn while a run is active; the model acts on `check` for cap and stop results. The Chief of Staff starts at most `cap - N` tickets per turn.
- `no hands off` ends in a drain that sets `paused` like other drains. `no hands` while `paused` is refused until `resume`.
- `no-hands` and `no hands off` are strict short-word commands in the user check. Added a short No Hands section to `README.md` and one sentence to `status.md`.
- Under a run, an unrated or non-string `status` counts as unrated and is auto-approved.
