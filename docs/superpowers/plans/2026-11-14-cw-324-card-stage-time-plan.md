# CW-324 plan: card stage and start time

Spec: `docs/superpowers/specs/2026-11-14-cw-324-card-stage-time-design.md`

## Task 1: `stageAt` in state (`agent-team/scripts/cos_state.py`)
- Add `stageAt` to `TICKET`.
- `op_start` sets `stageAt=now()`.
- `op_stage` sets `stageAt=now()` when `new != old`; same-stage ops leave it.
- A `set` (in `op_stage` or `op_set`) naming `stageAt` is rejected (`Reject`), like `lastSeenAt` in stamped stages. Keep `TICKET` usable for `check()`.
- Test (`test_cos_state.py`): one table over start, stage change, same-stage status rewrite, `set` of `stageAt` rejected.

## Task 2: API (`dashboard/groups.ts`, `dashboard/api.ts`)
- `Row`/`StatusRow` get `stageAt?: string`; `row()` copies it when a string; `buildApi` passes it through. Extend the existing api test.

## Task 3: Card (`dashboard/page/app.js`)
- `ticket()`: drop `next` (card and flat row). `sub` line begins with `<span class="badge stage">` for every row with a `stage` in every group: `stageWords(stage)` plus ` since HH:MM` via `clock()` when `stageAt` parses to a valid time, else the stage name alone. Leave `renderDetails` alone. Remove now-dead `next` code and CSS only if unused.
- Test (`page/app.test.js`): non-`Other` group row with `stageAt` and `next` shows stage and `since HH:MM`, not the `next` text; row without `stageAt` shows stage, no `since`. Fix existing tests that expect `next`.

## Task 4: Docs
- `agent-team/.claude/skills/chief-of-staff/state-keys.md`: add `stageAt` to the example and a key entry.

## Verify
`python3 -I -m pytest -q agent-team/scripts`; `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
