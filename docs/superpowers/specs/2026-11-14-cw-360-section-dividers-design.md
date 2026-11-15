# CW-360: Make the dividers between dashboard sections more prominent

**Status:** Draft
**Ticket:** [#360](https://github.com/collective-wisdom-org/collective-wisdom/issues/360)
**Builds on:** CW-346 (PR #352, merged), which added the rule under each section header. Other dashboard page tickets are in flight (CW-348, CW-349, CW-350, CW-354, CW-357, CW-359); this one changes two lines of CSS in `index.html` and rebases on whichever lands first.

## Goal

The line under each section header (Your turn, In progress, Up next, Not started, Done, and Project manager on the Chief of Staff tab) is easy to see in both themes, so each section start stands out while scrolling.

## Today

Facts from main at `247d285`, `agent-team/scripts/dashboard/page/index.html`.

- The `h2` rule (line 29) ends with `border-bottom:1px solid var(--line)`.
- `--line` is `light-dark(#e5e7eb, #ffffff14)` (line 11). In dark mode that is white at 8% opacity on a black page, close to invisible. In light mode it is gray-200 on `#fafafa`, faint.
- `--line` also draws the row dividers (`ul.rows > li.row`, `.grow`), the `.panel` and `.detail` top borders, the `.detail-section` and blockquote left borders, button borders and the `.seg .pill` background. Those stay as they are.

## Design

CSS only, in `index.html`. No markup, `app.js` or test changes.

1. A new colour token beside `--line`, used only by section dividers:

   ```css
   --section-line:light-dark(#d1d5db, #ffffff40);
   ```

   Light is gray-300, a step darker than `--line`. Dark is white at 25% opacity, which on the black page reads as about `#404040`, clearly lighter than the `#111111` cards and the `#1f1f1f` soft fill.

2. The `h2` rule's border becomes `border-bottom:2px solid var(--section-line);`. Everything else in that rule stays (size, weight, margins, `padding-bottom`).

Because `light-dark()` already follows `color-scheme`, the forced `data-theme="dark"` and `data-theme="light"` settings pick up the right value with no extra rules.

### Phone width

The border is a block border on the `h2`, so it spans the column inside the body gutter at any width, as today. One pixel more of height does not change layout.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/index.html` | Add `--section-line`; the `h2` border uses it at 2px. |

No new test: this is styling (`AGENTS.md` § Testing). The PR's proof is screenshots of the Ship loop tab in light and dark, at desktop and phone width, plus the Chief of Staff tab, with a before shot for comparison.

## Non-goals

- Section header text, size or spacing (CW-346).
- Row dividers, panel, detail and button borders, and the `--line` token itself.
- Any other dashboard page change from the in-flight tickets.

## Calls I made

- **`Project manager` gets the stronger line too.** It shares the `h2` rule; splitting it out would give that tab a second divider style for one heading.
- **Both a darker colour and a thicker line (2px).** The ticket allowed either; the colour alone stays thin in light mode, and the thickness alone barely helps at 8% opacity in dark mode.
- **A grey line, not the accent blue.** A coloured rule under every section would compete with the links and the amber "your turn" cards.
- **A new token rather than an inline colour,** so the light and dark values sit with the other theme tokens.
- **Values `#d1d5db` / `#ffffff40`.** Visible but quieter than the text; if they read too strong or too weak in the proof screenshots I tune them in the build and say so in `Differs from spec`.
