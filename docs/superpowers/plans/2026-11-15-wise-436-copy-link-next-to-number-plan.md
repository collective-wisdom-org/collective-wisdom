# WISE-436 plan: copy link next to the ticket number, avatar column, View PR / View spec

Spec: `docs/superpowers/specs/2026-11-15-wise-436-copy-link-next-to-number-design.md`. All paths under `agent-team/scripts/dashboard/page/` unless noted.

## Task 1: markup, labels, tests (`app.js`, `app.test.js`)

- `rowHead`: render `${idSpan}${extra}${title}${ownerHtml}`; update its doc comment.
- `ACTIONS`: `Open PR` to `View PR`, `Open spec` to `View spec`; update the `ticketRow` doc comment (line ~370).
- `app.test.js`: action table (lines ~136-137) and rendered match (~145) use the new labels; the copy-button test asserts `.id` span, then the button, then the `.title` span (and still no button without a thread link).
- Run `node --test agent-team/scripts/dashboard/page/app.test.js` (and the dashboard test command in `AGENTS.md`).

## Task 2: layout (`index.html`)

- `.head:has(> .id)`: `grid-template-columns: max-content auto minmax(0, 1fr) auto`.
- `.head .id`: `grid-column:1; grid-row:1`. `.head > .copy-icon`: `grid-column:2; grid-row:1`. `.head .title`: `grid-column:1 / 4; grid-row:2`. `.owner`: `grid-column:4; grid-row:1`, drop `justify-self:end` (use `justify-self:end` only if needed for the column to align right).
- Check in a browser that the number, button and avatar share row 1, the avatar is at the right edge, a long title wraps before the avatar column, and a card with no thread link or no owner looks right. Cos and role card heads unchanged.

## Task 3: README (`README.md` line ~187)

- `Open PR`/`Open spec` become `View PR`/`View spec`, and "the `Open spec` button" becomes "the `View spec` button".
- The copy button sits right after the ticket number (top-row sentence and the last sentence about "right after its title").
