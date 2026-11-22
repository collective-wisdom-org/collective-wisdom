# WISE-491: Add an x button to clear the red banner on the dashboard

**Status:** Draft
**Ticket:** [#491](https://github.com/collective-wisdom-org/collective-wisdom/issues/491)

## Goal

The red banner at the top of the dashboard gets an x button in its top right corner. Clicking it hides the banner, and the banner stays hidden while its text stays the same. A different message brings it back.

## Today

- `page/index.html` has `<p id="error" role="status"></p>` under the header. `#error` styles it red on `--red-tint`, and `#error:empty { display:none; }` hides it when it has no text.
- `showError()` in `page/app.js` sets its `textContent` to `restartError`, `trackerError` (from `/api`) and `pressNote` (the Approve or Start shipping press message), joined by spaces.
- `poll()` calls `showError()` on every refresh, and on a failed fetch writes `Could not refresh: <message>` into the same element.

## Change

1. **Markup** (`page/index.html`): the banner becomes a box with the message and the button side by side:

   ```html
   <div id="error" hidden>
     <p id="error-text" role="status"></p>
     <button type="button" id="error-dismiss" class="copy-icon" aria-label="Dismiss" data-tip="Dismiss"><svg ...>x</svg></button>
   </div>
   ```

   `role="status"` moves to the text, so screen readers still hear each new message and do not read the button. The button reuses the `copy-icon` look (borderless 1.5rem icon button, muted until hover) and the keyboard focus ring buttons already have. The x is a small inline SVG of two crossed strokes in `currentColor`.

2. **Style**: `#error` keeps its colours, padding and radius, and becomes a flex row (`display:flex; align-items:flex-start; gap`) with the text taking the space (`flex:1`, `margin:0`). The button sits at the top right and takes the banner's red as its colour. `#error:empty` is replaced by `#error[hidden] { display:none; }`, since the box is never empty now that it holds the button.

3. **Dismiss rule** (`page/app.js`): a new exported pure function

   ```js
   export const bannerShown = (text, dismissed) => text !== '' && text !== dismissed
   ```

   The page keeps `dismissed`, the banner text that was showing when the x was clicked (`''` at load).

4. **One writer**: a `setBanner(text)` helper inside the page's start-up code writes `text` into `#error-text` and sets `#error`'s `hidden` to `!bannerShown(text, dismissed)`. `showError()` calls it with the joined text, and `poll()`'s catch calls it with `Could not refresh: <message>`. Nothing else writes the banner.

5. **The click**: the x sets `dismissed` to the text on show and hides the banner. The next poll with the same text leaves it hidden. Any other text (a new message added, one dropped, a refresh failure, a new press note) shows it again. Once the banner text goes empty, `dismissed` is not cleared, so the same message coming back later stays hidden; see Calls I made.

6. **Test** (`page/app.test.js`): one table-driven test of `bannerShown`: empty text stays hidden with or without a dismissal; text with nothing dismissed shows; the dismissed text stays hidden; a changed text after a dismissal shows.

## Leaves out

- Other red marks on the page (the blocked x on cards, risk badges).
- What the messages say and when the server sets them.
- Remembering a dismissal across a page reload: a reload shows the banner again, as it does today.

## Calls I made

- **A message that clears and later comes back with the exact same text stays hidden.** The ticket says the banner stays hidden "for as long as its text is the same", so only a change in text brings it back. If `trackerError` goes away and the same error returns an hour later, the banner stays cleared until the text changes or the page reloads. The other choice, forgetting the dismissal once the banner goes empty, would show it again in that case; I kept the ticket's literal rule because it is simpler and a flapping error would otherwise keep reappearing.
- **The dismissal lives in page memory, not `localStorage`.** A reload shows the banner again, which matches today's "until the page reloads" and means a stale dismissal can never hide a real problem for long.
- **The comparison is on the whole joined text**, not per message. Adding or dropping one of the three parts changes the text and shows the banner again, which is what the ticket's "a new message shows up" asks.
- **`role="status"` moves from the box to the text**, so the button's name is not read out with every message.
- **The x reuses the `copy-icon` button style** (borderless icon button) and the `data-tip` popup the page already has, instead of a new button style.
- **The banner is hidden with the `hidden` attribute** instead of `:empty`, because the box always holds the button.
