# WISE-485 plan: instant styled tooltips

Spec: `docs/superpowers/specs/2026-11-21-wise-485-instant-styled-tooltips-design.md` (approved).

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` (Node 24+), then `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: markup and tests (`page/app.js`, `page/app.test.js`)

- Replace every `title="..."` the page builds (copy button, disabled segments, owner badge, `mark`, approve/changes links, Start shipping, gantt `.bar` in `ciBars` and `bars`, `.grow` row) with `data-tip="..."`, same text, same `esc`. Keep every `aria-label`.
- Copy handler `show`: set `data-tip` instead of `btn.title`.
- Disabled segment: `aria-disabled="true"` plus `data-tip`, no `disabled`; the segment click handler ignores `aria-disabled="true"`. Pagers keep `disabled`.
- Update `app.test.js` asserts from `title=` to `data-tip=` (and `disabled title` cases to `aria-disabled="true"`). Add one assertion that the rendered page fixtures contain no ` title="`.

## Task 2: popup and glow (`page/index.html`, `page/app.js` browser part)

- `<div id="tip" role="tooltip" hidden></div>` at the end of `<body>`; CSS per spec § 2 (`light-dark` tokens, `pre-line`, max-width ~22rem, `pointer-events:none`). `.seg[aria-disabled="true"]` looks like `button:disabled` (opacity .5, default cursor, no hover change). `.tipped` glow per spec § 3.
- Browser-only listeners (inside `typeof document !== 'undefined'`): `pointerover`/`focusin` show, `pointerout`/`focusout`/capture `scroll`/`Escape` hide. Text via `textContent`. Placement per spec § 2. `aria-describedby="tip"` while shown when `data-tip` differs from `aria-label`.
- `refreshTip` after each `draw` and after the copy handler changes `data-tip`: re-read the anchor's text, or re-find it with `elementFromPoint` at the last pointer position, else hide.
- No unit test for the browser listeners (spec § 5).
