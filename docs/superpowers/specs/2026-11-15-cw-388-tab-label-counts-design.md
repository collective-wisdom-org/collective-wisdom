# CW-388: Show ticket counts in the dashboard Ship loop and Done tab labels

**Status:** Draft
**Ticket:** [#388](https://github.com/collective-wisdom-org/collective-wisdom/issues/388)
**Related:** #371 (Agents button count; this reuses its `pill` look), #387 (adds a Backlog tab and moves Todo and Backlog off Ship loop; whichever builds second rebases on the other). Builds on #350 (the Done tab).

## Goal

The Ship loop and Done tab labels show how many tickets each tab holds, as a count pill, and the number stays current on every poll.

## Today

Facts from main at `fa0f78e`, in `agent-team/scripts/dashboard/page/`.

- `index.html` has three tab buttons with plain text: `tab-ship` "Ship loop", `tab-cos` "Chief of Staff", `tab-done` "Done". The tab panels take their names from the buttons through `aria-labelledby`.
- `.pill` (`index.html`) is the count pill used by the group headers and the Agents button. `.seg .pill` swaps its background to `--line` because the segment button sits on `--soft`.
- `.tabs` has a `--soft` background; the selected tab has a `--card` background.
- `renderBadges(groups)` sums group `count` per band from `BANDS` (Your turn, In progress, Up next) and leaves Not started out.
- `last.merged` is the full merged list (`buildApi` gets all of `merged.get()`, at most 200 PRs from `merged.ts`); `renderMerged` pages it in the browser.
- `drawStatus` and `drawMerged` redraw only when their html changed, and `selectTab` only toggles `aria-selected`, `tabIndex` and `hidden`.

## Design

### Counts (`app.js`)

A new exported pure function:

```js
/** Ticket counts for the tab labels: `ship` sums group `count` over the Your turn, In progress and Up next bands, `done` is the merged list length. */
export function tabCounts(status, merged) // → { ship: number, done: number }
```

- `ship` uses the same band sum as `renderBadges`, so the tab and the header line agree. The sum is pulled out into one small helper (`bandSum(groups, band)`) that both call, so the two cannot drift. Not started is not counted, so the number is the same before and after #387 moves Todo and Backlog.
- A missing or non-array `status` or `merged` counts as 0. A group `count` that is not a number counts as 0, as in `renderBadges` today.

### Markup (`index.html`)

Each counted tab button gets an empty pill after its text:

```html
<button … id="tab-ship" …>Ship loop <span class="pill tab-count" data-count="ship" aria-hidden="true"></span></button>
<button … id="tab-done" …>Done <span class="pill tab-count" data-count="done" aria-hidden="true"></span></button>
```

The Chief of Staff tab is unchanged.

### Updating (`app.js`)

A `drawTabCounts()` step runs on every successful poll, right after `drawStatus`, `draw`, `drawMerged` and `drawCos`, independent of whether their html changed. For each counted tab it:

- sets the pill's `textContent` to the number (0 shows `0`),
- sets the button's `aria-label` to `<label>, <n>` (for example `Done, 12`), with the label from a small map (`ship: 'Ship loop'`, `done: 'Done'`).

It writes only when the value changed, and touches nothing else on the button, so focus, `aria-selected`, `tabIndex` and the Arrow, Home and End keys behave as before. Before the first poll the pills are empty and the buttons keep their plain names.

The pill is `aria-hidden` and the count is in `aria-label`, so a screen reader reads "Done, 12, tab" once instead of "Done 12". The tab panels keep `aria-labelledby` the tab, so a panel's name also carries the count; that matches what a sighted reader sees.

### Styling (`index.html`)

- `.tabs .pill { background:var(--line); margin-left:var(--s1) }`, like `.seg .pill`, so the pill shows on the tab strip's `--soft` background. On the selected tab (`--card` background) `--line` still shows. Both colours already have dark-mode values.
- The pill is `inline-block` with `vertical-align:.05em`, so it sits on the text line. At phone width the three tabs plus two short pills still fit; the build checks this at 360px and lets the strip wrap with `flex-wrap:wrap` only if they do not.

### Tests (`app.test.js`)

One table-driven test for `tabCounts`, per `AGENTS.md` § Testing:

- A status sample with groups in each band (including a Not started group and a group whose `count` is missing) and a merged list of 3 gives `{ ship: <sum of the three bands>, done: 3 }`.
- Empty `status` and empty `merged` give `{ ship: 0, done: 0 }`.
- `undefined` for both gives `{ ship: 0, done: 0 }`.

The existing `renderBadges` tests keep passing after the shared sum is pulled out. `drawTabCounts` is DOM wiring and gets no test.

## Leaves out

- A count on the Chief of Staff tab, or on the Backlog tab #387 adds (#387 can call `tabCounts` or the band helper).
- Any change to the Agents button count or the group pills.
- Counting past the 200 merged PRs `merged.ts` reads.
- Server changes: the counts come from data the page already has.

## Calls I made

- **The pill is hidden from screen readers and the count goes in `aria-label`** ("Done, 12"), not in visible text read twice. The ticket asks for the count in the accessible name; this keeps it from being read as "Done 12 12".
- **The Ship loop sum shares one helper with `renderBadges`**, a small refactor of `renderBadges`, so the tab number and the "N need you · N in progress · N waiting" line cannot disagree. Blocked tickets in Up next count in the tab (they are on the tab), even though the header line lists them apart.
- **Before the first poll the pills are empty** and the tabs read as their plain names, rather than showing `0` that would be wrong for a moment.
- **The pill uses `--line` as its background on the tab strip**, the same override the Agents segment button uses, because the default `--soft` pill would vanish on the `--soft` tab strip.
- **Updates write only when the number changed**, so a poll does not touch the DOM for nothing.
- **No test for the DOM wiring**: the rule worth testing is the count, which `tabCounts` holds.
