# CW-317 plan: remove retired-thread forwarding

Spec: [design](../specs/2026-11-14-cw-317-remove-retired-thread-forwarding-design.md). Follow its "What changes" section file by file.

Test command: `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest -q agent-team/scripts` if pytest is missing).

## Task 1: Scripts and their tests

- `cos_state.py`: remove ops `retire`, `archive`, `unretire`, the helper, the `retiredThreads` default in `apply_ops`, its prune rule, `retiredThreads` in `TOP` and in the `top` op's allowed-key exclusion, the `retired:` line of `show`, and the docstring mentions.
- `cos_tick.py`: `stops()` returns `stop not-chief` when `chiefThreadId` is set and is not this thread; drop the `retiredThreads` reads (`stops`, `check_state`).
- `cos_peer.py`: sender must equal `chiefThreadId`; drop the `retiredThreads` read, its `Unreadable` case, and fix docstrings.
- Update `test_cos.py`, `test_cos_tick.py`, `test_cos_peer.py`, `test_cos_rank.py` as the spec says (drop retire/archive/unretire and bad-`retiredThreads` cases; keep one `stops()` row showing a leftover `retiredThreads` entry no longer stops the tick; keep one `cos_peer` row showing a non-chief thread is refused).

## Task 2: Skills and docs

Edit per the spec: `chief-of-staff/{rotation,SKILL,startup,ticket-helper,state-keys,continuation,report-format}.md`, `ship-loop/{SKILL,reference}.md`, `docs/compatibility.md` G26. Keep section pointers valid (`test_section_pointers.py`).

## Verify

Test command passes; `/usr/bin/grep -rnE "retiredThreads|Moved-to|Relay chain|unretire|stop retired" agent-team` finds nothing; `shellcheck` unaffected.
