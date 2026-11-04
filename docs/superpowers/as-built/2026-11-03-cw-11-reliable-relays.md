# As-built: Reliable Chief of Staff relays

**Shipped:** in PR #22
**Ticket:** CW-11 (#11)
**Spec:** [2026-11-03-cw-11-reliable-relays-design.md](../specs/2026-11-03-cw-11-reliable-relays-design.md)
**Plan:** [2026-11-03-cw-11-reliable-relays.md](../plans/2026-11-03-cw-11-reliable-relays.md)

## What shipped

- `scripts/cos_ready_check.py`: port of fathom's GUY-327 check. Prefix, repo and branch head come from `project_config`. `cos_brief.py` exposes `latest_review` so both scripts parse review verdicts the same way.
- `scripts/cos_sweep.py`: runs the merged check (with apply), the ready check and the parent check (no archive lines) in one process and prints `sweep: read in full: ...; merged: ...`. `cos_merged_check.py` and `cos_parent_check.py` gained `run()` entry points; their CLI output is unchanged.
- `scripts/cos_handoff.py` (GUY-258): the `HANDOFF` block for continuation children, with the branch, spec path and spec SHA checks that the skill did by hand.
- `chief-of-staff` SKILL.md: every merged-check call site runs the sweep; new § Sweep; the slot fill gate checks a full lane's children when it has a queue; the continuation template carries the handoff block; § Send or queue records why finish notices get lost. `ship-loop` and `merge-pr` treat the `HANDOFF` block as data.

## Why notices get lost

T3 sends a finish notice only to a child's parent thread, and only when that parent started the run or the run ended on a background-command wake. After a rotation, relays to an old child come from another thread, so nothing is sent. The thread also skipped the multi-step idle and parent checks that would find the finish. The sweep puts the checks that need no thread read behind one command.

## Differs from the spec

- `check()` in the ready check returns `(ticket, "ready" | "pushed")` pairs so the sweep can print the reason.
- A merged ticket is never `ready` (only `build` and `spec` tickets are candidates), so the sweep test for ordering checks that a merged ticket under an old parent is not also listed for a full read.
- `cos_handoff.py` requires `branch` and `stage`; a null `specPath` or `specSha` prints `Spec: none`. `reject:` values are collapsed to one line and capped at 100 characters.

## Verification

- `python3 -I -m pytest -q agent-team/scripts`: 309 passed. `shellcheck install.sh agent-team/scripts/*.sh`: clean.
- `cos_handoff.py` run against PR #10: checks and review lines match `cos_brief.py pr 10`.

## Not verified

- No live Chief of Staff thread has run the sweep yet.
