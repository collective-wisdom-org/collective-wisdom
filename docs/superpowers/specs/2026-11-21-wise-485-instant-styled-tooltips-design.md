# WISE-485: Replace dashboard title tooltips with instant styled hover popups

**Status:** Shipped
**Ticket:** [#485](https://github.com/collective-wisdom-org/collective-wisdom/issues/485)
**Shipped:** in PR #487, as specified

## Goal

Every dashboard tooltip shows the moment the pointer is over its element, in a popup styled like the rest of the page, and the hovered element glows a little while its popup shows. The browser's native `title` popup is gone from the dashboard.

## Today

All in `agent-team/scripts/dashboard/page/app.js`; `index.html` has no `title` attributes.

- `copyButton` sets `title="Copy thread link"`, and the copy click handler's `show` rewrites `btn.title` to `Copied` or `Copy failed`, then back after 1.5 s.
- `segments` gives a disabled segment `disabled title="${s.off}"` ("No agent sessions recorded", "No ticket yet"). Browsers fire no pointer events on a `disabled` button, so a script popup could never show on it.
- `ownerBadge` (`.owner`) and `mark` (epic icon, blocked icon, green check) carry `title` next to a matching `aria-label`.
- `approveControls` (Approve, Changes) and the Start shipping link carry a `title` explaining what the link types into the Chief of Staff thread. Their accessible name is the link text; the `title` is extra.
- Gantt: each `.bar` (`ciBars`, `bars`) and each `.grow` row (`rowTitle`) carries a multi-line `title`. Neither has an `aria-label`.
- `patchChart` patches the chart in place so the element under the pointer survives a poll tick. The cards and details bodies are rewritten through `innerHTML` when their html changes.

## Change

### 1. `data-tip` replaces `title` (`app.js`)

Every `title="..."` listed above becomes `data-tip="..."`, with the same text and the same `esc`. Every `aria-label` stays. The copy handler's `show` sets `data-tip` instead of `btn.title`.

A disabled segment becomes `aria-disabled="true"` instead of `disabled`, so it gets pointer and focus events. CSS gives `.seg[aria-disabled="true"]` the look `button:disabled` gives today (faded, default cursor, no hover change). The segment click handler, which checks `seg.disabled` today, ignores a segment with `aria-disabled="true"`. The Previous / Next pagers keep `disabled`: they have no tooltip.

### 2. One popup (`index.html`, `app.js`)

`index.html` gets one `<div id="tip" role="tooltip" hidden></div>` at the end of `<body>`, styled with the page tokens: `--card` background, `--fg` text, `--edge` ring and a small shadow, `--t-small` text, `white-space: pre-line` so multi-line text keeps its breaks, a max width of about 22rem, `pointer-events: none`. It uses the `light-dark()` tokens, so light and dark themes both work.

`app.js` (browser part) shows it from delegated listeners on `document`:

- `pointerover` / `focusin`: the nearest `[data-tip]` ancestor of the target becomes the anchor. The popup takes its `data-tip` as `textContent` (never html), unhides, and the anchor gets the `tipped` class. No delay.
- `pointerout` to an element outside the anchor, `focusout`, `scroll` (capture) and `Escape`: hide the popup and drop `tipped`.
- **Placement.** Below the anchor's bounding box with a 6px gap, horizontally centred on the anchor, then clamped to 8px inside the viewport. If it would run past the bottom, it goes above the anchor instead. Since it sits outside the anchor's box, it never covers the pointer while the pointer is on the anchor.
- **Accessible description.** While shown, an anchor whose `data-tip` differs from its `aria-label` (the approve links, Start shipping, a disabled segment) gets `aria-describedby="tip"`, removed on hide. The anchors with a matching `aria-label` lose nothing.

### 3. The hover cue (`index.html`)

`.tipped` gets a soft glow: a 2px `--accent` ring at low opacity via `box-shadow` (a `filter: drop-shadow` for `.mark` and `.owner`, which are icon shapes). Gantt bars get a slight brightness lift as well, since the ring alone is thin on a 6px bar. The glow shows exactly while the popup does.

### 4. Surviving updates (`app.js`)

After each `draw` and after the copy handler changes a `data-tip`, `refreshTip` runs:

- If the anchor is still in the document, re-read its `data-tip` (the text changes as a running bar's time grows, or to `Copied`) and re-place the popup.
- If it was replaced (a card rewritten by `innerHTML`), find the `[data-tip]` element under the last pointer position with `document.elementFromPoint` and anchor to it, or hide when there is none.

So the gantt bars, which `patchChart` keeps in place, keep their popup across a tick, and the other anchors do too.

### 5. Tests (`app.test.js`)

- Update every case that asserts `title="..."` to assert `data-tip="..."`, and the disabled segment cases to `aria-disabled="true"`.
- The marks test that checks the tooltip matches the accessible name reads `data-tip`.
- One new assertion over the full rendered page fixtures: no ` title="` in any markup `app.js` builds.

The popup listeners and placement run in the browser only (the `typeof document` part), like `patchChart`, so they have no unit test; they are checked by hand in both themes.

## Leaves out

- What any tooltip says.
- Touch-device behavior.
- Tooltips on elements that have none today (the pagers, the tabs).

## Calls I made

- **Disabled segments switch from `disabled` to `aria-disabled="true"`.** Browsers send no pointer events to a disabled button, so the popup can't show on one otherwise. They now take keyboard focus, which also lets the popup show on focus.
- **Screen readers get the extra text through `aria-describedby` only while the popup shows.** For the approve links, Start shipping and disabled segments, the `title` used to be an always-on description. A screen-reader user who tabs to them still hears it, because focus shows the popup. Gantt bars and rows were mouse-only before and stay so.
- **Any replaced anchor is re-found by the last pointer position**, not only gantt bars, so a popup on a card survives a tick that rewrites the card.
- **The popup goes below the element, flipping above near the bottom edge**, instead of following the pointer.
- **The glow is an accent ring, plus a brightness lift on gantt bars.**
- **Scroll hides the popup** rather than moving it with the page.
