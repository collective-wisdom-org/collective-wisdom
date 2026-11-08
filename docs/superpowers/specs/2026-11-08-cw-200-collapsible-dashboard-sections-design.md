# CW-200: Make dashboard status sections collapsible

**Status:** Draft
**Ticket:** [#200](https://github.com/collective-wisdom-org/collective-wisdom/issues/200)
**Related:** #195 redesigns the headings and cards; #198 (shipped in PR #201) changed the row order. Both touch the same section markup; this ticket changes only how a section opens and closes.

## Goal

The user can collapse and expand each status section on the dashboard. The choice holds across the 5-second poll and a page reload.

## Today

Facts from `main` at `3ab6621`.

- `renderStatus(groups, open)` in `agent-team/scripts/dashboard/page/app.js` draws one `<section class="group">` per group: an `<h3>` with the name and a count pill, then `<ul class="cards">`. Only the Agents chart in a card (`<details class="chart">`) opens and closes.
- `poll()` rebuilds `#status` only when the status JSON changed. Before it rebuilds, it reads the ticket ids of `details.chart[open]` from the DOM and passes them as `open`.
- Nothing in `page/` uses browser storage. The CSP from `server.ts` (`default-src 'self'; style-src 'self' 'unsafe-inline'`) allows `localStorage`.
- `renderBadges` counts from the data, so it doesn't care whether a section is open.
- `index.html` styles `h3` and `#status > .group:first-child h3 { margin-top:0 }`.

## Builds

1. **Markup.** Each status section becomes a native disclosure:

   ```html
   <details class="group" data-group="Awaiting merge approval" open>
     <summary><h3>Awaiting merge approval <span class="pill">2</span></h3></summary>
     <ul class="cards">…</ul>
   </details>
   ```

   The summary is the click and keyboard target (Tab, then Enter or Space), with no script. A closed section still shows its heading and count pill; its cards are hidden.
2. **`renderStatus(groups, open = new Set(), collapsed = new Set())`.** A section whose name is in `collapsed` is drawn without `open`. Every other section is drawn with `open`, so a section nobody touched is expanded. The name in `data-group` is escaped like all other text. The empty-state `No state yet` is unchanged.
3. **Memory in the browser.** The browser shell keeps the collapsed names in `localStorage` under one key, `cw-dashboard-collapsed`, as a JSON array of section names.
   - A `toggle` listener on `document` (capture phase, because `toggle` doesn't bubble) handles `details.group`: closed adds its name, open removes it, and the list is written back. The handler reads `details.open`, so it is the same whether the user or a rebuild fired it.
   - `poll()` reads the stored list and passes it to `renderStatus` as `collapsed` when it rebuilds `#status`. The stored list, not the DOM, is the source, so a reload starts with the same sections closed.
   - Names are kept even while their section is absent from the data, so a section that empties out and comes back keeps its state.
   - If storage can't be read or written (blocked, full, bad JSON), the page treats the list as empty and keeps working; a failed write leaves the choice in place until the next reload.
4. **Styles in `index.html`.** The heading sits on one line with the disclosure marker before it: the `h3` inside the summary is inline, the summary has `cursor:pointer`, and the first-section rule becomes `#status > .group:first-child h3`, which still matches. A visible focus outline stays (the browser default).
5. **Test.** One table-driven test in `page/app.test.js`: with `collapsed` empty every section has `open`; a named section loses `open` while the others keep it; the closed section still has its heading and pill; a name with markup is escaped in `data-group`. The existing chart `open` test keeps passing.
6. **Docs.** The dashboard paragraph in `README.md` says each stage section collapses from its heading and the page remembers it in the browser.

## Leaves out

- The Merged list. It is not a status section.
- Section order, ticket order (#198) and the visual redesign (#195).
- Collapse all and expand all.
- Remembering the choice across browsers or machines.
- The status-pane mod.

## Calls I made

- **Native `<details>`/`<summary>`, not a button with `aria-expanded`.** It is keyboard reachable and announced as expandable without script, and it matches the Agents chart already on the page. The heading stays an `<h3>` inside the summary, so screen-reader heading navigation still finds each section.
- **The section element changes from `<section>` to `<details>`.** The class `group` stays, so the existing styles and the first-section rule keep working. #195 rebases onto this if it lands second.
- **Store collapsed names, not expanded ones.** Expanded is the default, so a new section the team adds later shows up open.
- **Keyed by section name.** The ticket asked for it. Renaming a section (as CW-177 did) forgets its state, which leaves it open: the safe side.
- **One storage key for all repos on the same port.** Each repo's dashboard runs on its own localhost port, and `localStorage` is per origin, so two repos don't share a list.
- **No test of the browser shell.** The `toggle` listener and storage calls run only in the browser, like the copy button and the pager today. The rule that can break quietly, which sections draw open, lives in `renderStatus` and is tested.

## Touches

None of these: data, money, auth, user email, migrations.
