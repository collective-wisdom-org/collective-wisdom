# As-built: Reset the Chief of Staff session in place

**Shipped:** in PR #333
**Ticket:** CW-316
**Spec:** [2026-11-14-cw-316-reset-session-in-place-design.md](../specs/2026-11-14-cw-316-reset-session-in-place-design.md)

## Differs from the spec

- Spec § 8 (context size from T3's store) was left out. No table of T3's store on the version CW-315 ran holds a context size, so `read_context()` still reads only the transcript and Codex keeps no size trigger.
- The CW-315 record leaves two checks unconfirmed: the context size after a reset (G30) and a child's finish notice reaching the new session (G29). Claude Code still gets `reset`, since the reset itself passed; both are listed under Not proven in the PR.
- `cos_state.py`'s `top` op drops a leftover `rotation` or `rotationHeldUntil` from any state it touches, and validates `reset` (null, or an 8-hex `id`, a zoned `startedAt`, a `reason`, an optional `mode`) and `lastResetAt`.
- A missing or malformed `chiefProvider` in state is mode `none`, shown as `unknown` in the line `ok (no reset on unknown; ...)`.
- A stale `reset` marker ends the `rotate:` line with `; mode <mode>; reset never confirmed`.
- `cos_sweep.py` changed too: it called `cos_parent_check.run(..., archive=False)`, which no longer takes that argument.
- Take over is now four steps, so pointers in `SKILL.md`, `kill-switch.md` and `sweep.md` use steps 3 and 4 where they named steps 4 and 5.
