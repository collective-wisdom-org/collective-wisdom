# CW-369: Make the dashboard top-level section headers collapsible

**Status:** Shipped
**Shipped:** in PR #383, with differences: [as-built](../as-built/2026-11-15-cw-369-collapsible-top-headers.md)
**Ticket:** [#369](https://github.com/collective-wisdom-org/collective-wisdom/issues/369)
**Related:** #349 (edits `renderStatus`), #350 (moves Done to its own tab), #370 (row cards). None has a PR open today; whichever builds second rebases on the other.

## Goal

A reader can collapse each top-level section of the dashboard (Your turn, In progress, Up next, Not started, Done, and Project manager on the Chief of Staff tab) the way the sub-sections already collapse, and the page remembers the choice through the 5-second poll and a reload.

## Today

Facts from main at `90d7a68`, in `agent-team/scripts/dashboard/page/`.

- `renderStatus` (`app.js`) draws each band as `<section class="band band-<slug>"><h2>name</h2>…</section>` from `BANDS`. `renderChief` returns `${card}<h2>Project manager</h2>${pm.html}`. `index.html` holds a static `<h2>Done</h2>` above `<div id="merged">`.
- Sub-sections are `<details class="group" data-group="<API group name>">` with `<summary><h3>…</h3></summary>`. The chevron is `summary::after`, turned by `details[open] > summary::after`.
- Collapsed names are a JSON array of strings in `localStorage` under `cw-dashboard-collapsed` (`readCollapsed`, `writeCollapsed`, both try/catch). A capture-phase `toggle` listener on `document` handles `details.group` only. `#status` is redrawn only when the status JSON changed, with `readCollapsed()` each time.
- `drawCos` redraws `#cos` only when `renderChief`'s html changed. `drawMerged` writes only `#merged`, so a Done header outside it is never redrawn.
- CSS that names the band `h2`: `.band:first-child > h2 { margin-top:0 }` and `.band > h2 + .group > summary { margin-top:var(--s2) }`. The `h2` rule itself carries the size, margins and the `--section-line` border (CW-360).

## Design

### Markup

Each top-level section becomes a `<details>` whose `<summary>` holds the existing `<h2>`:

```html
<details class="band band-needs" data-band="band:needs" open><summary class="band-head"><h2>Your turn</h2></summary>…sub-sections…</details>
```

- Bands: `renderStatus` keys each band as `band:<slug>` (`band:needs`, `band:progress`, `band:queued`, `band:not-started`) and leaves `open` off when `collapsed` has that key. Its signature does not change.
- Done: the static `<h2>Done</h2>` and `<div id="merged">` in `index.html` become `<details class="band band-done" data-band="band:done" open><summary class="band-head"><h2>Done</h2></summary><div id="merged">…</div></details>`. On start-up, before the first poll, the page drops `open` from it when `band:done` is in the saved set. Nothing redraws that element afterwards, so the browser's own state carries it through polls.
- Project manager: `renderChief(api, page, open, size, collapsed = new Set())` wraps the heading and the list as `<details class="band band-pm" data-band="band:pm" …><summary class="band-head"><h2>Project manager</h2></summary>${pm.html}</details>`. `drawCos` passes `readCollapsed()` to both of its `renderChief` calls, so the comparison and the redraw agree and a poll keeps the state.
- The key goes through a small exported `bandKey(slug)` that returns `band:<slug>`. The prefix contains a colon; no API group name (the `GROUPS` list in `groups.ts`, plus `Todo` and `Backlog`) does, so a band and a sub-section never share an entry.

`<details>` and `<summary>` give mouse, Enter and Space, an accessible name from the `h2` text, and the expanded state, as the sub-sections have. The `h2` stays a heading inside the summary, so heading navigation still finds it.

### Saving

The `toggle` listener also handles `details[data-band]`: it adds or removes `d.dataset.band` in the same array. `readCollapsed` and `writeCollapsed` are unchanged, so an array saved before this change still reads, and blocked storage or bad JSON still gives an empty set (everything open).

Collapsing a band only hides its content. The sub-section `<details>` inside keep their own `open` state and their own entries, so they come back as they were.

### Styling (`index.html`)

- `summary.band-head` is a block; the `h2` inside keeps its rule (size, margins, border) unchanged, so the text, look and spacing stay.
- The chevron: `summary.band-head::after` is turned off, and the same chevron is drawn on `summary.band-head > h2::after`, so it sits after the heading text and above the line instead of below it. `details[open] > summary.band-head > h2::after` turns it, like the sub-sections.
- The two selectors that named the band `h2` move to the summary: `.band:first-child > summary > h2 { margin-top:0 }` and `.band > summary + .group > summary { margin-top:var(--s2) }`.
- `summary:focus-visible` already draws the focus ring.

### Tests (`app.test.js`)

One table-driven test, per `AGENTS.md` § Testing:

- `renderStatus` with an empty set draws every band open; with `bandKey('needs')` in the set the Your turn band has no `open` while its sub-sections keep theirs; with a group name in the set only that group closes.
- `renderChief` with `bandKey('pm')` drops `open` from the Project manager section, and without it keeps `open`.
- Every band key (from the band slugs, plus `done` and `pm`) starts with `band:` and none equals a name in the group list the page knows, so the two never collide.

The existing `bandsOf` test reads `<h2>…</h2>` and keeps passing.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | Bands and Project manager as `<details data-band>`; `bandKey`; `renderChief` takes `collapsed`; start-up applies the Done state; the toggle listener handles bands. |
| `agent-team/scripts/dashboard/page/index.html` | Done wrapped in `<details>`; band-head chevron and the two moved selectors. |
| `agent-team/scripts/dashboard/page/app.test.js` | The test above. |

Proof: screenshots of the Ship loop tab with a band collapsed and all open, Done collapsed, and Project manager collapsed, in light and dark at desktop and phone width.

## Non-goals

- Collapse-all or expand-all controls.
- Collapsing the Chief of Staff card.
- Changing the sub-section collapse, the band order or the Done list content.
- Moving Done to its own tab (#350).
- A count on the band `h2`.

## Calls I made

- **The chevron sits after the heading text, above the divider line,** drawn on the `h2` rather than the summary, so the line under the header stays full width and the chevron does not drop below it.
- **Keys are `band:needs`, `band:progress`, `band:queued`, `band:not-started`, `band:done`, `band:pm`,** taken from the existing slugs, so renaming a band's text does not lose its saved state.
- **The band element changes from `<section>` to `<details>`.** The class names stay (`band band-<slug>`), so the existing styling that targets `.band` keeps working; only the two `> h2` selectors move.
- **Done's state is applied once at start-up** instead of being redrawn, since that element sits in `index.html` and nothing rewrites it.
- **`renderChief` gets a fifth `collapsed` parameter** rather than reading storage itself, so it stays a pure function the tests can call.
- **No change to `renderBadges`** or any count.

## Changed after approval

- #350 merged before this build: Done is now its own tab and has no `h2` on the Ship loop tab. The ticket says to keep the Done header collapsible only if it still exists, so the build drops the Done band, its `<details>` wrapper, its `band:done` key and the start-up step. The other five sections are as specified.
