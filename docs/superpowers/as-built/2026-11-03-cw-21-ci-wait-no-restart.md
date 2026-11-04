# As-built: Stop restarting children that only wait on CI

**Shipped:** in PR #34
**Ticket:** CW-21 (#21)
**Spec:** [2026-11-03-cw-21-ci-wait-no-restart-design.md](../specs/2026-11-03-cw-21-ci-wait-no-restart-design.md)
**Plan:** [2026-11-03-cw-21-ci-wait-no-restart.md](../plans/2026-11-03-cw-21-ci-wait-no-restart.md)

## What shipped

- `scripts/cos_idle_check.py --wait <ticket>`: port of fathom's GUY-328 check. Reads one `t3_thread_read` result (activity view) on stdin and prints `waiting`, `stalled <reason>` (`no-wait`, `unmatched`, `wait-expired Nm`) or a `cos_idle_check:` line with exit 2. It counts only items of `recentRuns[0]`, treats a wait that ended within 45 minutes as waiting, and handles a wait call whose text was cut off. The existing mode is unchanged.
- `chief-of-staff` SKILL.md § Full pass step 3: a `completed` run with no marker goes through the wait check first. `waiting` means no restart and no change to `restarts`. `stalled` restarts once, then blocks, quoting the line. An unreadable check can restart but never blocks, and adds a Cleanup line. The "Text about waiting is no exception" sentence is gone.
- `chief-of-staff.md` § Done when: the restart line says "unless it is waiting on a background command".
- `ship-loop` SKILL.md § Team mode: "Run endings" and "CI waits" tell a child to start background commands with the tool's option, never `&`, to start again on an `unmatched` wait, and to keep the wait among its last few tool calls.
- One table-driven test for `--wait` in `test_cos_idle_check.py`: the six rows from the ticket plus two cut-off-text rows.

## Differs from the spec

- The ship-loop "Run endings" sentence no longer says "the thread stays Working", because it contradicts "T3 shows the run as `completed`".
- The "Otherwise `stage` op to `blocked`" bullet in step 3 gained one sentence: a `completed` run with no marker is blocked only on a `stalled` line. Without it an exit 2 on a second stall would fall into that bullet and block the ticket.

- A cut-off wait call gives exit 2 only while the run ended within 45 minutes. Older, it reads `stalled ... wait-expired`. Found in security review pass 1: exit 2 never blocks, so an unlimited exit 2 would let a child hold its slot for good.
- The intro of chief-of-staff SKILL.md (line 23) also gained "unless the wait check says it is waiting", found by the docs check.

## Verification

- `python3 -I -m pytest -q agent-team/scripts`: 335 passed.
- `shellcheck install.sh agent-team/scripts/*.sh`: clean.
