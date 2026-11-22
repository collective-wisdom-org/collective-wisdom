# WISE-492: Keep the dashboard tab counts on one line

**Status:** Shipped
**Ticket:** [#492](https://github.com/collective-wisdom-org/collective-wisdom/issues/492)
**Shipped:** in PR #493, with differences: [as-built](../as-built/2026-11-22-wise-492-tab-counts-one-line.md)

## Goal

Each dashboard tab (Ship loop, Backlog, Done, Chief of Staff) shows its label and count pill on one line at any window width. When the window is narrower than the tab bar, the bar scrolls sideways and the page does not.

## Today

- `agent-team/scripts/dashboard/page/index.html`: `.tabs` is `display:inline-flex` with no width limit or overflow rule. `.tabs button` has no `white-space` or `flex-shrink` rule, so a narrow window shrinks the buttons and the pill wraps under the label. `body` sets `overflow-wrap:anywhere`, which lets a label break too.
- `.pill` is `display:inline-block; min-width:1.6em`, so a three-digit count (Done 191) is the widest pill and wraps first.
- `agent-team/scripts/dashboard/page/app.js`: `selectTab(name, { save, focus })` sets `aria-selected`, `tabIndex` and the panel's `hidden`, and calls `tab.focus()` only when `focus` is true (the arrow, Home and End handler passes it). On page load it runs with the saved tab and no focus, so nothing scrolls a saved tab into view.

## Change

1. `index.html` CSS:
   - `.tabs` adds `max-width:100%; overflow-x:auto;` and keeps `display:inline-flex`, so the bar is as wide as its tabs, never wider than `main`, and scrolls sideways when it can't fit.
   - `.tabs button` adds `flex:none; white-space:nowrap;`, so a button never shrinks below its label plus pill and the two stay on one line.
2. `app.js` `selectTab`: for the selected tab, call `tab.scrollIntoView({ block: 'nearest', inline: 'nearest' })` when `focus` is false (the `focus()` call already scrolls a focused tab into view). This keeps a saved tab visible on load and after a click on a partly hidden tab.

No change to `tabCounts`, the pill style outside the tab bar, the panels, or the keyboard handler.

## Proof

- Screenshots of the dashboard at about 320px and 1280px wide with real counts, and one with a four-digit count put in the Done pill by hand in the browser, showing one line per tab.
- At 320px: the bar scrolls sideways, `document.documentElement.scrollWidth` equals the window width (no page scrollbar), and Home, End and the arrows move the selection with the selected tab in view.
- The dashboard tests in `AGENTS.md` § Testing pass.

## Leaves out

- Which counts the tabs show (`tabCounts` in `app.js`).
- The layout of the panels under the tabs.
- New tests: this is styling plus one scroll call, which `AGENTS.md` § Testing says not to test.

## Calls I made

- The bar scrolls with the browser's own horizontal scrollbar (thin on macOS, shown only while scrolling); no hidden scrollbar, fade edges or arrow buttons.
- The selected tab is kept in view with `scrollIntoView({ block: 'nearest', inline: 'nearest' })`, which moves the page only if the bar itself is off screen; at load the bar sits at the top, so the page doesn't jump.
- The bar keeps its current look (inline width, soft background, 3px padding); only overflow and wrapping change.
- No README change: the README describes the tabs but not how the bar lays out.
