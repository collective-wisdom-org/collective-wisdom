# CW-413: Move the dashboard Gantt legend below the chart

**Status:** Draft
**Ticket:** [#413](https://github.com/collective-wisdom-org/collective-wisdom/issues/413)

## Goal

Each dashboard Gantt chart shows its color legend at the bottom, under the Total row and any cost notes, instead of above the first row.

## Today

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` (around line 682) builds `legendHtml`, a `<ul class="legend">` with one item per drawn category, and puts it first inside `<div class="gantt">`, before the rows. The Total row and the two `.gnote` paragraphs follow the rows.
- `agent-team/scripts/dashboard/page/index.html` styles `.legend` with `margin:0 0 var(--s2)` (gap below it), and `.grow:first-child, .legend + .grow { border-top:0; }` removes the top border from the first row whether or not a legend comes before it.
- `agent-team/scripts/dashboard/page/app.test.js` (around line 720) asserts the markup starts with `<div class="gantt">\n<ul class="legend"`.

## Design

1. **Markup (`page/app.js`).** Build the same `legendHtml` (same swatches, labels, order and `aria-label`), but emit it last inside `<div class="gantt">`: rows, Total row, `note`, `oldNote`, then the legend. The trailing newline moves to the front of the string so the closing `</div>` stays on its own line. No drawn category still means an empty string and no `<ul>`.
2. **Spacing (`page/index.html`).** Change `.legend` to `margin:var(--s2) 0 0`, so the gap sits above it, matching the Gantt's own padding below. Reduce the first-row rule to `.grow:first-child { border-top:0; }`: with the legend gone from the top, the first row is the first child again and nothing else needs `.legend + .grow`.
3. **Test (`page/app.test.js`).** Replace the "starts with the legend" assertion with one that the legend `<ul>` comes after the Total row and is the last element before `</div>`. Keep the existing assertions on category order and on no legend for an empty chart.

## Leaves out

- The legend's colors, labels, order and wrapping.
- Any change to rows, the Total row or the cost notes.

## Calls I made

- The legend goes after the cost notes, not between the Total row and the notes, because the ticket asks for it as the last element in the chart.
- The gap above the legend is `var(--s2)`, the same size as the old gap below it, rather than the smaller `var(--s1)` the notes use. It reads as its own block, not as another note.
- No new test file or test case: the existing Gantt markup test gets its position assertion changed, per `AGENTS.md` § Testing.

## Verification

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.
- `python3 -I -m pytest -q agent-team/scripts` passes.
