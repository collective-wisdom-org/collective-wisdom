# CW-411: Reorder the dashboard tabs and add a Backlog tab count

**Status:** Draft
**Ticket:** [#411](https://github.com/collective-wisdom-org/collective-wisdom/issues/411)
**Related:** #388 (the Ship loop and Done tab pills this copies), #387 (the Backlog tab).

## Goal

The dashboard tab bar reads Ship loop, Backlog, Done, Chief of Staff, and the Backlog tab shows a ticket count pill like the Ship loop and Done tabs.

## Today

Facts from main at `c400910`, in `agent-team/scripts/dashboard/page/`.

- `index.html` lists the tab buttons as Ship loop, Chief of Staff, Done, Backlog (lines 174 to 177), and the four panels (`panel-ship`, `panel-cos`, `panel-done`, `panel-backlog`) follow in the same order.
- `selectTab` and the ArrowLeft, ArrowRight, Home and End handler in `app.js` work on `[...document.querySelectorAll('button[role="tab"]')]`, so they follow the DOM order of the buttons.
- `tabFromStorage` picks the saved tab from `localStorage` key `dashboard-tab`, falling back to `ship`. The `ship` button is the one marked `aria-selected="true"` and `tabindex="0"` in the markup.
- The Ship loop and Done buttons carry `<span class="pill tab-count" data-count="…" aria-hidden="true"></span>`. `.tabs .pill:empty { display:none; }` hides a pill until it has a number.
- `tabCounts(status, merged)` returns `{ ship, done }`. `drawTabCounts` runs on every poll; for each `[data-count]` pill it writes the number and sets the button's `aria-label` to `<TAB_LABELS[key]>, <n>`. `TAB_LABELS` is `{ ship: 'Ship loop', done: 'Done' }`.
- The Backlog group's header pill in `renderBacklog` shows `g.count` of the status group named `Backlog`.

## Design

### Order (`index.html`)

Move the buttons to Ship loop, Backlog, Done, Chief of Staff, and move the panels to the same order so the file reads in tab order. Ids, `aria-controls`, `aria-labelledby`, `aria-selected`, `tabindex` and `hidden` stay as they are on each element. Ship loop stays first and selected in the markup, so it is still the default. Nothing in `app.js` changes for the order: the keys and `selectTab` already follow the DOM.

### Backlog pill (`index.html`, `app.js`)

- The Backlog button gets the same empty pill: `Backlog <span class="pill tab-count" data-count="backlog" aria-hidden="true"></span>`. The existing `.tabs .pill` rules style it and hide it while empty, so it stays hidden until the first poll.
- `tabCounts` also returns `backlog`: the `count` of the group named `Backlog` (the `BACKLOG` constant), as a number. A missing group, or a `count` that is not a number, gives 0. This is the same number the Backlog group header shows.
- `TAB_LABELS` gains `backlog: 'Backlog'`, so `drawTabCounts` writes the pill and sets the button's `aria-label` (for example `Backlog, 12`) with no other change to it.
- The `tabCounts` doc comment names the new key.

### Tests (`app.test.js`)

The existing table-driven `tabCounts` test gains `backlog` in each expected result: the sample status (which already holds `Backlog` with count 9) gives `backlog: 9`, and the empty and `undefined` rows give `backlog: 0`. One more row covers a `Backlog` group whose `count` is not a number, giving `backlog: 0`. The button order and the DOM wiring get no test, per `AGENTS.md` § Testing.

## Leaves out

- Renaming tabs, changing what a tab shows, or changing the default tab.
- Any change to the Ship loop or Done counts, or to the header line from `renderBadges`.
- A count on the Chief of Staff tab.
- Server changes: the count comes from the status the page already polls.

## Calls I made

- **The Backlog count is the group's `count`, not the number of rows loaded.** The ticket names `count`, and it matches the group header pill, so the two never disagree. When the list is longer than the rows the dashboard holds, the tab shows the full count.
- **A non-number `count` gives 0**, as the Ship loop sum already does, rather than hiding the pill.
- **The panels move along with the buttons.** Only the button order matters to the page; moving the panels just keeps the file readable in tab order.
- **No test for tab order or key movement.** That behaviour comes from DOM order with no code change, and the repo has no DOM test harness for the page.
