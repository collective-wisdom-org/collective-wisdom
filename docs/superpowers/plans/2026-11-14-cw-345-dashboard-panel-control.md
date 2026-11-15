# CW-345 plan: one Agents and Details control and a waiting counter

**Spec:** [2026-11-14-cw-345-dashboard-panel-control-design.md](../specs/2026-11-14-cw-345-dashboard-panel-control-design.md) (approved at commit 3518973)
**Ticket:** [#345](https://github.com/collective-wisdom-org/collective-wisdom/issues/345)

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Task 1: panel switch markup (`page/app.js`)

- Add `panelSwitch(scope, id, { gantt, view, details })` per spec § 1 and § 2; remove `chartToggle` and the hand-built `details.info` pairs in `ticket()`, `renderMerged` and `teamList`.
- `.foot` starts with the switch; the panels (`.panel`, `hidden` unless open) follow `.foot` inside the `li`. Keep `.chart-body[data-*]` and `.info-body[data-*]` classes and attributes.
- Agents disabled (`Agents 0`) with no panel when there are no tasks; helper cards get a disabled Details; pm rows Agents only, pm meta moves into the foot.
- Renderers still take the `open` and `info` sets; Agents wins when an id is in both.
- Merged rows fill the Details body only when open (as today).

## Task 2: behaviour (`page/app.js`)

- Click on `.seg`: flip `aria-expanded` and `hidden` on both panels of the row (one open at a time), then `draw()`. Escape closes the open panel and focuses its segment.
- Open-state reads in `poll`, `drawMerged`, `drawCos` use the `.seg[...][aria-expanded="true"]` selectors of spec § 6. The `toggle` listener keeps only `details.group`.

## Task 3: waiting counter (`page/app.js`)

- Export `waitText(stageAt, now)` per spec § 7.
- `awaiting-*` cards: `<p class="wait" data-ticket><time datetime title>` replaces `<p class="next">`; none when `stageAt` is missing. `stageSentence` drops ` since HH:MM` for `awaiting-*`. `blocked` keeps `next`.
- `draw()` refreshes `.wait[data-ticket] time` text in place, writing only on change.

## Task 4: CSS (`page/index.html`)

- Add `.switch`, `.seg`, `.panel`, `.wait` per spec § 3 (2.25rem segments under 30rem). Remove `.foot .summary, .foot .meta { margin-right:auto }` and the `.foot > details*` rules.

## Task 5: tests (`page/app.test.js`)

- Rewrite the tests listed in spec § Tests that move.
- Add three tables: `waitText`; one rule over every row type (switch first in `.foot`, same order, one open panel at most, no-task row has disabled Agents and no Agents panel); `awaiting-*` counter vs `build` `next` vs missing `stageAt`, with the full `next` in Details.
- No tests for CSS, click or Escape handling (`AGENTS.md` § Testing).

## Task 6: doc line

- `agent-team/.claude/skills/chief-of-staff/state-keys.md`, `stageAt` bullet: one sentence saying the card shows a live `waiting …` counter for `awaiting-*` stages. Do not change how status is written.
