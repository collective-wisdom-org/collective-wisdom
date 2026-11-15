# CW-353 plan: finish an interrupted take over

Spec: [design](../specs/2026-11-14-cw-353-finish-take-over-design.md). Test command: `python3 -I -m pytest -q agent-team/scripts`.

1. `cos_state.py`: add `takeover` to the top keys (null, or `{"startedAt": zoned time not in the future, "mode": "take-over"|"resume"}`, nothing else); show it as `takeover=<mode> since <time>` or `takeover=-`. Add rows to the `test_cos_state.py` table for the top op.
2. `cos_rotation_check.py` `decide()`: after the `paused` hold, a dict `takeover` returns `finish: take over unfinished since <N>m; mode <mode>`. Rows in `test_decide` (ahead of a fresh `reset` hold and the size trigger; null gives today's line) and one hook row (blocks once).
3. `cos_tick.py`: every look plan except `start` begins with the single line `follow rotation.md § Thread rotation: Finish take over` when `takeover` is set (before the provider check); `--after-reads` is unchanged. Rows in `test_cos_tick.py`.
4. Docs, `agent-team/.claude/skills/chief-of-staff/`: `state-keys.md` (the key); `rotation.md` (step 1 sets the key, resume mode sets it, step 4 clears it with `skillCommit`, step 2 clears it when it stops, step 2 finds the newest `CHIEF OF STAFF RESET` message within 100 items, new "Finish take over" paragraph, `finish:` in the line list); `SKILL.md` (§ Turn start bullet, `finish:` beside `rotate:` in the rotation-check table row).
5. Run the test command, `shellcheck` is not touched. Compaction pass on the changed skill text.
