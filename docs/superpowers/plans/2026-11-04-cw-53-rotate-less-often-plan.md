# CW-53 plan: rotate the Chief of Staff thread less often

Spec: [2026-11-04-cw-53-rotate-less-often-design.md](../specs/2026-11-04-cw-53-rotate-less-often-design.md). All paths below are under `agent-team/`.

1. `scripts/cos_state.py`
   - Add `lastRelayAt` to `TOP`. `op_top` rejects it (`keys_ok` allowed set drops it).
   - `op_start`: when it creates a ticket, set `s["lastRelayAt"] = now()`. An existing ticket (the early return) does not stamp.
   - `op_stage`: when `new in ACTIVE and new != old`, set `s["lastRelayAt"] = now()`.
   - `show`: print `lastRelayAt=<t()>` with the rotation keys. `prune` leaves it (it is in `TOP`).
2. `scripts/cos_rotation_check.py`
   - Remove `AGE_HOURS`, `AGE_MIN_CONTEXT` and the age branch; `decide()` no longer takes `started`.
   - Add `QUIET_RELAY_MIN = 10`, `QUIET_ROTATED_MIN = 60`. New `quiet_wait(state, now)` returns the wait reason or `None`, first that applies: `queued <ID>` (any ticket whose stage ends `-queued`; lowest id first), `relay <N>m ago` (`lastRelayAt` under 10 minutes old), `rotated <N>m ago` (newest `retiredAt` under 60 minutes old).
   - Skill change on `main`: if `quiet_wait` returns a reason, remember `ok (skill change waits: <reason>)` and fall through to the size check (size wins and ignores quiet); otherwise `rotate: skill changed ...`. With no size trigger, return the waits line instead of the plain `ok context=` line. The `size trigger off` note keeps its place ahead of the waits line.
   - `--record-takeover` prints `; take-over context=<N>k` appended to the line.
   - Update the module docstring if it names age.
3. Tests (one table each, as in the spec)
   - `test_cos_rotation_check.py::test_decide`: drop the age rows and the `hours` column; add rows for a queued ticket, relay 5 and 11 minutes ago, rotation 30 and 61 minutes ago, size beating a non-quiet skill change.
   - `test_cos.py`: one table that `start` and a `stage` op into an active stage stamp `lastRelayAt`, a move into `awaiting-spec` does not, and a `top` op that sets it is rejected.
   - `test_plain_saves_session_and_takeover`: add the `take-over context=` check as a column.
4. Docs
   - `.claude/skills/chief-of-staff/rotation.md` § Thread rotation: trigger table (no Age row; skill change adds the quiet rule), the constants line, the quiet-turn rule and the `skill change waits` line, take-over step 5's post (`... <N> tickets in flight. Take-over context <K>k.`).
   - `.claude/skills/chief-of-staff/state-keys.md`: a `lastRelayAt` bullet; `skillCommit` bullet says the change waits for a quiet turn. `SKILL.md` state sample gets `"lastRelayAt": null`.
   - `docs/agents/chief-of-staff.md`: drop "age"; the skill change waits for a quiet turn.
5. Verify: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh`.
6. Commit, open the PR (builder), closeout docs, docs check, code review, security review, per ship-loop § Team mode. Note on CW-53 that the compaction test was not run and raising the cap is left for later.
