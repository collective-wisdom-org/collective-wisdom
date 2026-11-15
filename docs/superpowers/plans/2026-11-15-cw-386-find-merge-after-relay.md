# CW-386 plan: find a merge after a merge relay

Spec: `docs/superpowers/specs/2026-11-15-cw-386-find-merge-after-relay-design.md`

1. `agent-team/scripts/cos_route.py`: line 136 prints `merge-wait: <T>` for every merge-lane send (drop `and not parent`); keep the `moving:` line only when `not parent`. Update the docstring line for `merge-wait:` ("a merge-lane send: start the merge wait").
2. `agent-team/scripts/cos_tick.py`: line 222 appends `merge-wait <T>` for every merge send (drop `and not parent`); fix the comment and the docstring sentence near line 15 ("A `send <T> merge` is followed by `merge-wait <T>`").
3. `agent-team/scripts/test_cos_route.py`: in `test_the_merge_lane_starts_the_merge_wait`, flip the `("approve-merge", "awaiting-merge", ME, ...)` row to `wait=True`.
4. `agent-team/scripts/test_cos_tick.py`: add `merge-wait` after every `send <T> merge` that currently lacks it, and one row for a queued merge under this thread (parent equal to the chief thread) that gets `merge-wait ABC-1`.
5. `agent-team/.claude/skills/chief-of-staff/sweep.md` § Merge wait: opening sentence covers every merge send (a finish notice can be lost even when this thread is the parent); starts list says `cos_route.py` and the tick print it for every merge send; `still open` no longer says the Moving line told the user (still runs the tick once, starts no new wait).
6. `agent-team/.claude/skills/chief-of-staff/status.md` rules: a `Merging` row's Next comes from this turn's merged check: `PR #N open, merge sent <time>` while the PR is open, not "merge in progress" from the relay alone.
7. `agent-team/.claude/skills/chief-of-staff/SKILL.md` `send` row and `continuation.md`/`send-or-queue.md`: check wording still true; edit only if it says the wait depends on the parent.
8. Run `python3 -I -m pytest -q agent-team/scripts`.
