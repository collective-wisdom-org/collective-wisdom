# CW-346: Make the dashboard section headers stand out more

**Status:** Shipped
**Shipped:** in PR #352, as specified
**Ticket:** [#346](https://github.com/collective-wisdom-org/collective-wisdom/issues/346)
**Builds on:** CW-266 (PR #340, merged), the redesign whose header rule this changes. Runs beside CW-345 (Agents · Details control), which changes the card foot and not the headers; whichever builds second rebases on the other.

## Goal

The five section headers on the Ship loop tab (Your turn, In progress, Up next, Not started, Done) read as section breaks, not labels, so each is easy to find while scrolling.

## Today

Facts from main at `6e85821`.

- `renderStatus()` in `agent-team/scripts/dashboard/page/app.js` draws each of the four `BANDS` as `<section class="band band-<slug>"><h2>name</h2>…</section>`.
- Done is a plain `<h2>Done</h2>` in `agent-team/scripts/dashboard/page/index.html`, above `#merged`.
- One rule styles every `h2`: `font-size:var(--t-band)` (0.6875rem, 11px), uppercase, `letter-spacing:.08em`, weight 600, `color:var(--muted)`, `margin:var(--s8) 0 var(--s3)`. `.band:first-child > h2` drops the top margin.
- That is smaller than the group titles under it (`h3`, 0.9375rem, weight 600, `--fg`) and the ticket titles, so the eye lands on the groups first and the bands blur together.
- The same rule styles `<h2>Project manager</h2>` on the Chief of Staff tab (`renderChief()`).
- `--t-band` is also used by `.info-grid dt` and `.detail-head` inside Details. Those keep it.
- `app.test.js` reads band names with `/<h2>([^<]+)<\/h2>/`.

## Design

CSS only. The `h2` markup and text stay as they are, so no test changes and no collision with CW-345's `app.js` work.

### The rule

In `index.html`, a new size token `--t-section:1.125rem` (18px), and the `h2` rule becomes:

```css
h2 { font-size:var(--t-section); line-height:1.3; font-weight:650; letter-spacing:-.005em;
     color:var(--fg); margin:var(--s8) 0 var(--s3); padding-bottom:var(--s2);
     border-bottom:1px solid var(--line); }
```

- Sentence case: the names are already written `Your turn`, `Up next`, so dropping `text-transform:uppercase` shows them as written.
- Size order on the page becomes h1 1.375rem > h2 1.125rem > h3 0.9375rem, so the bands now sit clearly above the groups.
- Full-contrast `--fg` instead of `--muted`. Weight 650 matches `h1`.
- A hairline rule under the name, in `--line`, runs the width of the column and marks where each section starts. The token already has light and dark values, so dark mode needs no extra rule.
- `.band:first-child > h2 { margin-top:0 }` stays, so the first band still sits right under the tabs.
- The `.band > h2 + .group > summary { margin-top:var(--s2) }` spacing stays; with the rule and padding it gives the first group a little air under the line.

### Done

Done is an `h2` too, so the one rule covers it. It sits after `#status` with the same `--s8` top margin as the bands between themselves, so it reads as the fifth section.

### Project manager

`Project manager` on the Chief of Staff tab shares the rule and gets the same look. It is the only section header on that tab, under the Chief of Staff card, and the larger name with a rule under it reads as a section start there too. Nothing on that tab is restyled beyond it.

### Phone width

At 360px the longest name (`Not started`) is about 100px at 18px, so nothing wraps. The rule spans the column inside the 16px body gutter as today.

### Before and after

```
Before                               After

YOUR TURN                            Your turn
Ready to merge  (2)                  ─────────────────────────
┌ card ┐ ┌ card ┐                    Ready to merge  (2)
                                     ┌ card ┐ ┌ card ┐
IN PROGRESS
Building  (3)                        In progress
┌ card ┐ ┌ card ┐ ┌ card ┐           ─────────────────────────
                                     Building  (3)
                                     ┌ card ┐ ┌ card ┐ ┌ card ┐
```

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/index.html` | Add `--t-section`; rewrite the `h2` rule as above. |

`app.js` and `app.test.js` do not change. No new test: this is styling (`AGENTS.md` § Testing). The PR's proof is screenshots of the Ship loop tab in light and dark, at desktop and phone width, and of the Chief of Staff tab.

## Non-goals

- Which tickets sit in which band, the band names, or their order.
- The Agents · Details control and the waiting counter (CW-345).
- The Chief of Staff tab layout beyond the shared `Project manager` header.
- Group (`h3`) and card styles.

## Calls I made

- **No count next to the band name.** It would change the `h2` markup that `app.test.js` parses and that CW-345 renders around, and the header sentence above the tabs already counts the bands. The groups keep their own count pills.
- **No band colour.** All five headers look the same, including Your turn; the amber tint on its cards already says "your turn". The ticket asks for one consistent look.
- **Not sticky.** A pinned header while scrolling would help find your place, but needs a background, a z-index over cards and Gantt, and a check against the tabs. A later ticket if wanted.
- **Sentence case instead of uppercase.** Uppercase at 18px shouts; the names are already written in sentence case.
- **Size 1.125rem (18px)**, between the group titles and the page title, and weight 650 to match the title.
- **A full-width hairline under the name** rather than a thick accent bar, so it marks the break without adding a colour.
- **`Project manager` takes the new look** since it shares the rule; splitting it out would keep a second header style for one heading.
- **`--t-band` stays** for the small uppercase labels inside Details, which this ticket does not touch.
