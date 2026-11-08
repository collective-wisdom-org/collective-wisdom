# CW-225 plan: gantt task rows show own work, bars get tooltips

Spec: `docs/superpowers/specs/2026-11-08-cw-225-gantt-own-spans-design.md`

## Task 1: app.js

In `renderGantt` (`agent-team/scripts/dashboard/page/app.js`):

1. `bars(spans, stale)` becomes `bars(row, spans)`. Each `.bar` gets `title="${esc(...)}"`: line 1 `row.r.name`; line 2 `<range> · <duration> · <model>` with parts joined by ` · `. Range is `clock(a), running` when `open && !row.s.stale`, else `clock(a) to clock(b)`. Duration is `duration(b - a)` of the merged span. Model is `row.r.model`, left out when null, undefined or empty.
2. The task row calls `line(i, i.spans, cost, 0)`. Drop the `all` union. Keep the `active` axis, the cost sum and the Total unchanged.

## Task 2: app.test.js

- Rewrite the case "a task row includes its subagents once..." to "a task row shows only its own time; ..." with want `['t|2m 00s|$1.75', 'x|2m 00s|$0.50', 'y|1m 00s|$0.25', 'Total|3m 00s|$1.75']`, and bars where the task row has none over the subagent-only time.
- Add one test for the bar tooltip: markup in the name and a model, one closed bar and one running bar; assert the escaped title text of both.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
