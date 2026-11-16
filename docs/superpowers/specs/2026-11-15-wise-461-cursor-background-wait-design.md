# WISE-461: Background waits on Cursor (G32)

**Status:** Shipped
**Ticket:** [#461](https://github.com/collective-wisdom-org/collective-wisdom/issues/461)
**Shipped:** in PR #472, as specified

## Goal

The team stops calling `t3_background_wait` on Cursor, where T3 refuses it, and waits another way. A Cursor child waits for CI in the foreground. A Cursor Chief of Staff starts no merge wait or run wait.

## Today

Facts from main at `69e8093`.

- On Cursor, `t3_background_wait` returns `This provider cannot mark background work as awaited.` (WISE-441, `docs/compatibility.md` G32). A shell command started in the background still runs, but nothing wakes the thread when it exits, so a turn that ends on it never resumes.
- `ship-loop/SKILL.md` § Run endings and § CI waits tell a child to start `wait-for-ci.sh` (and any other background command) with the background option, call `t3_background_wait`, and end the turn. `open-pr/SKILL.md` § CI review mode step 2 points to § CI waits.
- `wait-for-ci.sh` has a bound: up to 5 minutes for checks to show, then `gh pr checks --watch` until they finish. Two runs are the only time limit § CI waits sets.
- `chief-of-staff/sweep.md` § Merge wait and § Run wait start `cos_merge_wait.py` (30 minutes) and `cos_run_wait.py` (110 minutes) in the background and call `t3_background_wait`. They exist only to recover a lost finish notice. `session.md` lists `t3_background_wait` among the Chief of Staff's tools for those two sections.
- `cos_route.py` prints `run-wait:` and `merge-wait:` lines on every send, without knowing the harness.
- A child that waits in the foreground keeps its run `running`. `cos_idle_check.py`, `cos_run_wait.py` and the Stop hook's `late-child:` line already treat a running child as working, and a completed run with no marker and no matched wait as stalled, so no script needs to change.

## Design

Markdown only.

### 1. Ship loop on Cursor

`ship-loop/SKILL.md` § Run endings gets one rule: on Cursor, run a command you would wait on in the foreground, with a timeout long enough for it (`wait-for-ci.sh`: 20 minutes), and read its last line in the same turn. Never call `t3_background_wait` there. The other wait rules in § Run endings (end the turn after the wait, `unmatched`) apply only where the wait works. § CI waits says "as a background command" becomes "as in § Run endings", so it covers both. Exit codes and retries in § CI waits are unchanged.

### 2. Chief of Staff on Cursor

`sweep.md` gets one paragraph above § Merge wait: on Cursor, skip § Merge wait and § Run wait. Ignore `merge-wait` and `run-wait` plan lines and the `run-wait:` and `merge-wait:` lines of `cos_route.py`. A lost finish notice is then caught by the Stop hook's `late-child:` line (`~/.cursor/hooks.json`), the next user message, or the idle check of the next tick, whatever wakes it. The Chief of Staff must not run these waits in the foreground: that blocks the thread for up to 110 minutes, and the user's messages queue behind it. `session.md`'s tool list says the same in its `t3_background_wait` clause.

### 3. Compatibility

`docs/compatibility.md`: the G32 note, the 2026-11-15 run bullet and the gap list entry say Cursor waits in the foreground (children) or not at all (Chief of Staff) since WISE-461, with what is not yet seen in a run: a foreground `wait-for-ci.sh` on Cursor finishing within the shell tool's limit, and a lost finish notice caught on Cursor.

## Leaves out

- Script changes: no harness check in `cos_route.py`, `cos_idle_check.py` or the wait scripts.
- A T3 change to make `t3_background_wait` work on Cursor (upstream takes no feature PRs).
- Codex and Antigravity, where background waits are untested.
- A new Cursor trial run to prove it (a later run checks it).

## Calls I made

- The Chief of Staff on Cursor skips merge and run waits instead of waiting in the foreground. Those waits only back up a lost finish notice, and a 30 to 110 minute foreground block would make the Chief of Staff deaf to the user. Cost: a lost notice on Cursor waits for the Stop hook, the user or the next tick.
- Children on Cursor wait for CI in the foreground. `wait-for-ci.sh` is bounded and the child has nothing else to do while it waits. If Cursor's shell tool caps or backgrounds a long command, this breaks; that is not proven yet.
- The rule lives in the skills, not the scripts. The agent knows its own harness (the skills already say "on Cursor" elsewhere), and `cos_route.py` has no reliable way to know it.
- 20-minute foreground timeout for `wait-for-ci.sh`: 5 minutes for checks to appear plus this repo's CI time, with room.
- Markdown only, so per `kickoff-feature` there is no plan and no new test.

## Acceptance

- No skill tells a Cursor session to call `t3_background_wait`.
- `ship-loop` and `sweep.md` each say what Cursor does instead, in one place.
- `docs/compatibility.md` no longer says G32 has no path, and lists what is still unproven.
- The test command passes (`test_agent_files.py` and `test_call_sites.py` still pass on the edited skills).
