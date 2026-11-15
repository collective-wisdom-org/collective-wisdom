# CW-413: Move the dashboard Gantt legend below the chart and the ticket number above the title

**Status:** Shipped
**Ticket:** [#413](https://github.com/collective-wisdom-org/collective-wisdom/issues/413)
**Shipped:** in PR #418, as specified

## Goal

Each dashboard Gantt chart shows its color legend at the bottom, under the Total row and any cost notes, instead of above the first row.

Each ticket card's top row shows the ticket number on its own line, with the title and the thread copy button on the line below it. The user added this to CW-413 when the first spec came back, after CW-402 merged the current card layout.

## Today

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` (around line 682) builds `legendHtml`, a `<ul class="legend">` with one item per drawn category, and puts it first inside `<div class="gantt">`, before the rows. The Total row and the two `.gnote` paragraphs follow the rows.
- `agent-team/scripts/dashboard/page/index.html` styles `.legend` with `margin:0 0 var(--s2)` (gap below it), and `.grow:first-child, .legend + .grow { border-top:0; }` removes the top border from the first row whether or not a legend comes before it.
- `agent-team/scripts/dashboard/page/app.test.js` (around line 720) asserts the markup starts with `<div class="gantt">\n<ul class="legend"`.
- `rowHead()` in `page/app.js` (line 294) draws the card top row as `<div class="head"><span class="id">…</span><span class="title">…</span>…</div>`, with the copy button as the last child. Ticket cards (`ticket()`, line 353) pass the thread copy button; a ticket helper card's id is the text `Ticket helper`. Done cards (`renderMerged()`, line 451) use the same `rowHead()` with no copy button.
- `page/index.html` lines 55 to 59 lay `.head` out as one flex row: `.id` (muted, no wrap), then `.title`, then `.copy-icon`. Project manager rows (line 477) and the Chief of Staff card (line 493, overridden by `.cos-card .head` on line 104) also use `.head`, but with no `.id`.
- Root `README.md` says the chart has "a legend above the chart" and "The top row is the ticket number (linked to the issue), the title and a copy button".

## Design

1. **Markup (`page/app.js`).** Build the same `legendHtml` (same swatches, labels, order and `aria-label`), but emit it last inside `<div class="gantt">`: rows, Total row, `note`, `oldNote`, then the legend. The trailing newline moves to the front of the string so the closing `</div>` stays on its own line. No drawn category still means an empty string and no `<ul>`.
2. **Spacing (`page/index.html`).** Change `.legend` to `margin:var(--s2) 0 0`, so the gap sits above it, matching the Gantt's own padding below. Reduce the first-row rule to `.grow:first-child { border-top:0; }`: with the legend gone from the top, the first row is the first child again and nothing else needs `.legend + .grow`.
3. **Test (`page/app.test.js`).** Replace the "starts with the legend" assertion with one that the legend `<ul>` comes after the Total row and is the last element before `</div>`. Keep the existing assertions on category order and on no legend for an empty chart.
4. **Card top row (`page/index.html`, CSS only).** A head that holds a ticket number becomes a two-row grid: `.head:has(> .id) { display:grid; grid-template-columns:minmax(0, max-content) auto; justify-content:start; align-items:start; column-gap:var(--s1); }` and `.head .id { grid-column:1 / -1; }`. The number (still muted and linked to the issue) fills the first row. The title sits on the second row, wrapping inside its column, with the copy button right after it. The markup and `rowHead()` do not change, so the existing head tests keep passing and no new test is added (styling, per `AGENTS.md` § Testing). This applies to every `rowHead()` card: ticket cards, ticket helper cards (`Ticket helper` above the request title) and Done cards. Project manager rows and the Chief of Staff card have no `.id` and keep their one-row head.
5. **Docs (`README.md`).** Change "with a legend above the chart" to "with a legend below the chart", and the top-row sentence to say the ticket number sits above the title and the copy button.

## Leaves out

- The legend's colors, labels, order and wrapping.
- Any change to rows, the Total row or the cost notes.
- The top row of project manager rows and the Chief of Staff card.
- The card's middle and bottom rows.

## Calls I made

- The legend goes after the cost notes, not between the Total row and the notes, because the ticket asks for it as the last element in the chart.
- The gap above the legend is `var(--s2)`, the same size as the old gap below it, rather than the smaller `var(--s1)` the notes use. It reads as its own block, not as another note.
- The ticket number goes above the title on Done cards and ticket helper cards too, not only on Ship loop ticket cards, because they share `rowHead()` and one card layout was the point of CW-402.
- The copy button stays right after the title (second row), not next to the number, so the README's "copy button right after its title" still holds.
- The top row change is CSS only, using `:has()`, so `rowHead()` markup and its tests stay as they are. The T3 browser pane is Chromium, which supports `:has()`.
- No new test file or test case: the existing Gantt markup test gets its position assertion changed, per `AGENTS.md` § Testing.

## Verification

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.
- `python3 -I -m pytest -q agent-team/scripts` passes.
