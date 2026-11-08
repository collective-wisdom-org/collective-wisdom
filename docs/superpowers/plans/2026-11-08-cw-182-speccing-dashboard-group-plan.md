# CW-182 plan: a Speccing dashboard group

Spec: `docs/superpowers/specs/2026-11-08-cw-182-speccing-dashboard-group-design.md`

## Tasks

1. `groups.ts`: add `{ name: 'Speccing', stages: ['spec'] }` before `Awaiting build approval`; `Other` keeps `spec-queued` and `blocked`.
2. `status.md`: group table row, `Other` row, sample block, and the `Other` reasons rule.
3. `groups.test.ts`: expect `Speccing` with CW-6 and `Other` with CW-5.

## Verify

`node --test agent-team/.claude/mods/status-pane/hooks/*.test.ts agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` and `python3 -I -m pytest -q agent-team/scripts`.
