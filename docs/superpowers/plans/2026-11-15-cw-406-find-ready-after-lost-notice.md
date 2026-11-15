# CW-406 plan: find a ready child after a lost finish notice

Spec: `docs/superpowers/specs/2026-11-15-cw-406-find-ready-after-lost-notice-design.md` (approved). Work in `agent-team/`. Test command: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Task 1: `cos_child_read.py` scans back for a marker

- Add a function `find_marker(con_or_rows, thread, after)` used by both `read()` and the new wait: among finished assistant messages with rank > `--after` (all runs, newest first), return the newest one whose text matches `MARKER`, else None. Only when the newest run is `completed` (a running run still prints just `marker none`).
- `read()`: `head`, `next=` stay from the newest message. `item=`, `marker`, `field`, `block:`, `cut` come from the message with the marker. No marker anywhere: unchanged output (`marker none` + `tail:` of the newest message).
- Update the docstring.
- Tests in `test_cos_child_read.py` (table-driven, follow its existing fixtures): newest message no marker + earlier marker in same run; same, earlier run; earlier marker at or before `--after` not reported (tail instead).

## Task 2: `cos_run_wait.py`

Shaped like `cos_merge_wait.py` (Cannot, decide, wait with injected clock/sleep/readers, Parser, main). Usage `cos_run_wait.py <PREFIX>-N [--file STATE] [--db PATH] [--every S=30] [--for S=6600]`. Behaviour exactly as spec § 1, using Task 1's `find_marker` (after = ticket `lastPosition`). Lines: `run-wait: <T> left <lane>`, `run-wait: <T> run <status>`, `run-wait: <T> <BUILD READY|MERGE READY|BLOCKED|MERGED>`, `run-wait: <T> still working after 110m` (exit 1), `run-wait: cannot <what>` (exit 2). Marker grace: after a marker shows, one more round, re-read the ticket, then print. Store reads read-only (`mode=ro`), schema errors -> Cannot. Read only: writes nothing.
- Test `test_cos_run_wait.py`: one table-driven test of the per-round decision/`wait()` with fakes: left the lane, still running, no new run since send, failed run, completed no marker keeps waiting, completed with marker needs grace round (and prints `left` if ticket moved during grace), time up.

## Task 3: route and tick

- `cos_route.py`: `route: send spec|build` prints `run-wait: <T>` after the stage line (like merge-wait). Continuation `fallback:` line for spec/build adds " and start the run wait". Update docstring.
- `cos_tick.py`: `send <T> spec|build` plan line followed by `run-wait <T>`; update docstring. Also for the `continuation` path: nothing.
- Tests: `test_cos_route.py` rows (spec and build send print it; queue, continuation, merge don't); `test_cos_tick.py` one row for a queued spec approval send.

## Task 4: docs (skills under `agent-team/.claude/skills/chief-of-staff/`)

Per spec § 3-5: `sweep.md` new `## Run wait` after Merge wait (steps as spec § 4; background `timeout: 7200000`); update its intro line (read-this list) and `SKILL.md` files table row for sweep.md; `SKILL.md`: `run-wait <PREFIX>-N` row in Tick table, `send` row mention, wake list sentence (line ~115: add a run wait that ends), Marker paragraph (marker from newest message after `lastPosition` that holds one), `session.md` script list + `t3_background_wait` mention, `send-or-queue.md` (`route: send` copies `run-wait:` line, opening line names `run-wait`), `readiness.md` (Todo start starts the run wait after the start op), `continuation.md` (spec/build continuation child starts it), and the stuck-check restart / approvals.md send-backs (start the run wait when child stays in spec/build). Keep wording tight, no em dashes. Check any other doc listing script names (e.g. `agent-team/docs`, README) with grep for `cos_merge_wait` and add `cos_run_wait` where the merge wait is listed; also check `test_agent_files.py`/`test_call_sites.py` expectations.

## Verify

Run the full test command and shellcheck; show output. Do not commit; the parent reviews and commits.
