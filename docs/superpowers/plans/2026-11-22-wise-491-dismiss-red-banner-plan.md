# WISE-491 plan: dismiss the red dashboard banner

**Spec:** [2026-11-22-wise-491-dismiss-red-banner-design.md](../specs/2026-11-22-wise-491-dismiss-red-banner-design.md)

## Task 1: the rule and its test

- `page/app.js`: add `export const bannerShown = (text, dismissed) => text !== '' && text !== dismissed`.
- `page/app.test.js`: import it; one table-driven test (empty hidden with or without a dismissal, text with nothing dismissed shows, dismissed text hidden, changed text shows).
- Run: `node --test agent-team/scripts/dashboard/page/app.test.js`.

## Task 2: markup, style, wiring

- `page/index.html`: replace `<p id="error">` with `<div id="error" hidden>` holding `<p id="error-text" role="status">` and a `copy-icon` button `#error-dismiss` (aria-label and data-tip "Dismiss", inline SVG x). `#error` becomes a flex row; drop `#error:empty`, add `#error[hidden]{display:none}`; the button takes the banner's red.
- `page/app.js` start-up code: `dismissed = ''`, `setBanner(text)` writes `#error-text` and sets `hidden = !bannerShown(text, dismissed)`, remembering the current text. `showError()` and `poll()`'s catch call it. The x click sets `dismissed` to the current text and hides the banner.
- Run the full dashboard tests: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, then the Test command from project.md.
