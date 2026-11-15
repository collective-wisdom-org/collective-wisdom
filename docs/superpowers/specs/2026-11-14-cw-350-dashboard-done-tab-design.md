# CW-350: Move the dashboard Done list to its own Done tab

**Status:** Shipped
**Shipped:** in PR #376, as specified
**Ticket:** [#350](https://github.com/collective-wisdom-org/collective-wisdom/issues/350)

## Goal

The merged tickets get their own `Done` tab, after `Chief of Staff`. The Ship loop tab shows only the live work.

## Today

Facts from `main` at `6e85821`.

- `agent-team/scripts/dashboard/page/index.html` has a tablist with two buttons, `tab-ship` (`data-tab="ship"`, Ship loop) and `tab-cos` (`data-tab="cos"`, Chief of Staff), each with a `tabpanel`. `panel-ship` holds `#status`, then `<h2>Done</h2>` and `<div id="merged">`.
- In `app.js`, `renderMerged` builds one page of merged rows (meta line, Agents chart toggle, Details, Newer/Older pager). `drawMerged` writes it into `#merged`, only when the html changed, keeping open charts and Details. `drawCharts` and the Details fill find their bodies by `data-merged` anywhere in the document.
- `tabFromStorage(value)` returns `cos` for `'cos'` and `ship` for anything else, so a saved `done` would open Ship loop.
- `selectTab`, the click handler and the arrow/Home/End handler work from the list of `button[role="tab"]`, by `data-tab` and `aria-controls`. They take a third tab without changes.
- Nothing measures element width, so drawing the list inside a hidden panel is fine. Both tabs already keep updating while hidden.
- `app.test.js` checks `tabFromStorage` in one table: `['cos', 'ship', null, undefined, 'x', 'COS', 5]`.
- README `## Dashboard` says "Below the cards, a Done list shows ..." and "The page has two tabs, Ship loop and Chief of Staff".

## Design

1. **Markup** (`index.html`):
   - Add a third button after Chief of Staff: `<button type="button" role="tab" id="tab-done" data-tab="done" aria-selected="false" aria-controls="panel-done" tabindex="-1">Done</button>`.
   - Add `<div id="panel-done" role="tabpanel" aria-labelledby="tab-done" hidden>` after `panel-cos`, holding the `<div id="merged"><p class="quiet">Loading</p></div>` that moves out of `panel-ship`.
   - Remove `<h2>Done</h2>` from `panel-ship`. The tab name is the heading now, as the Chief of Staff panel has no `h2` either.
2. **Saved tab** (`app.js`): `tabFromStorage` returns `'cos'` or `'done'` when the value is exactly that string, else `'ship'`. Unknown values still fall back to Ship loop.
3. **No other code changes.** `#merged` keeps its id, so `drawMerged`, the pager, `drawCharts`, the Details fill and the poll's `mergedPage` work as they do. Open charts and Details stay open across a poll the same way.
4. **Test** (`app.test.js`): extend the `tabFromStorage` table with `'done'` → `'done'` and `'DONE'` → `'ship'`. The merged list tests run on `renderMerged` and do not change.
5. **Docs** (`README.md` § Dashboard): the Done list paragraph says it is on the Done tab instead of "below the cards", and the tabs paragraph names three tabs, Ship loop, Chief of Staff and Done.

## Leaves out

- What counts as done, the page size (ten), the 200 cap and the merged row content.
- A count on the Done tab label.
- The Backlog pagination in #349, and the other dashboard tickets in flight (#345, #346, #347).
- `api.ts`, `merged.ts` and the server: the API is unchanged.

## Calls I made (surprising first)

- **No count on the tab.** The Done tab reads `Done`, with no number like the Backlog heading has. The list already shows its pages, and a count that only grows says little.
- **The `Done` heading goes.** The ticket asks to remove the heading and list from Ship loop; I don't repeat it inside the new panel, since the selected tab already names it and the Chief of Staff panel has no heading either.
- **Exact match for the saved value.** `done` opens the Done tab, `DONE` does not, matching how `cos` works today.
- **README updated in this PR.** The two README sentences that place the Done list under the cards and say "two tabs" would be wrong after the change, so they change here rather than in the docs check.
- **No test for the markup.** The tab order and the move are static HTML, and `selectTab` and the key handler are untouched DOM code. I will check them by hand in the browser instead of adding a DOM test, per `AGENTS.md` § Testing.
- **Rebase risk.** #345 and #346 also edit `index.html` and `app.js`. This change is a few lines in the tablist and panels, so I will rebase on `main` before building and resolve any overlap then.

## Touches

None of these: data, money, auth, user email, migrations.
