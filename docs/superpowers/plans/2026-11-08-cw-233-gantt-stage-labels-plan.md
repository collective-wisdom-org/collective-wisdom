# CW-233 plan: gantt stage labels

Spec: `docs/superpowers/specs/2026-11-08-cw-233-gantt-stage-labels-design.md`

## Task 1: stage and role names in `taskName`

- In `mods/agent-gantt/hooks/timeline.ts`, `taskName` names a `Run /ship-loop for <ticket>:` line `<Stage> <ticket>: <title>` and the three helper first lines by role, as the spec's Design says. The stage needs the whole prompt text, so detect `CONTINUE` before it is stripped.
- In `timeline.test.ts`, update the `Run /ship-loop for CW-9: fix` rows and add one table for the cases the spec's Tests section lists.
- Bump `mods/agent-gantt/.claude-plugin/plugin.json` to 0.1.8.
- Verify: `node --test mods/agent-gantt/hooks/*.test.ts agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js`, then `python3 -I -m pytest -q agent-team/scripts`.
