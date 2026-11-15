# WISE-436: Move the copy thread link control next to the ticket number on dashboard cards

**Status:** Draft
**Ticket:** [#436](https://github.com/collective-wisdom-org/collective-wisdom/issues/436)

## Goal

On a ticket card the copy thread link button sits right after the ticket number, on the number row, instead of after the title.

## Today

Facts from main at `8c018e1`, `agent-team/scripts/dashboard/page/`.

- `app.js` `rowHead(idHtml, title, extra, ownerHtml)` renders `.head` as `.id`, `.title`, then `extra`, then the owner badge.
- Two callers pass an `.id`: `ticketRow` (Status and Backlog cards, and the `Ticket helper` card), whose `extra` is `copyButton(r.threadLink, { thread: true })`, and the Done cards in `renderMerged`, whose `extra` is `''`. Role cards and the Chief of Staff card build their own `.head` without `.id` and do not call `rowHead`.
- `copyButton` returns `''` when there is no thread link.
- `index.html`: `.head:has(> .id)` is a grid, `minmax(0, max-content) auto 1fr`. `.head .id` and `.owner` both span `1 / -1` in row 1, `.owner` with `justify-self: end`. The title and the button auto-place into row 2, columns 1 and 2, so the button follows the title.

## Design

### Markup (`app.js`)

- `rowHead` renders `extra` right after the `.id` span and before the title: `.id`, `extra`, `.title`, owner badge. The doc comment says so.
- The `rowHead` signature and its callers stay the same. `ticketRow` is the only caller with a non-empty `extra`, so only ticket cards change; Done cards render the same markup as before.

### Layout (`index.html`)

- In the `.head:has(> .id)` grid, place the items explicitly instead of by auto-placement:
  - `.head .id`: column 1, row 1.
  - `.head > .copy-icon`: column 2, row 1.
  - `.head .title`: row 2, spanning `1 / -1`, so it takes the full card width and wraps there.
  - `.owner`: row 1, spanning `1 / -1`, `justify-self: end`, as now.
- Column 1 becomes `max-content` (the number never wraps, it is `white-space: nowrap` already), so the button sits right after the number whatever the title length or card width.
- With no thread link there is no button, column 2 is empty, and nothing follows the number. The title row is unchanged.
- The `.head .copy-icon` top-margin nudge stays; check it still lines up with the number in the browser and drop or adjust it only if it no longer does.
- `.cos-card .head` and the role card head (no `.id`) are not touched.

### Tests (`app.test.js`)

- Tighten the existing `threadLink becomes a copy button` test so it asserts the order: the `.id` span, then the button, then the `.title` span. Layout is CSS and gets no test, per `AGENTS.md` § Testing.

## Acceptance

- On a ticket card the button is directly right of the ticket number, on the same line, and the owner avatar stays pinned to the card's right edge.
- The title is on its own line below, with no button after it.
- The `Ticket helper` card shows the button next to its label.
- A ticket with no thread link shows no button and no gap.
- A long title or a narrow card does not push the button off the number row.
- Done cards, role cards and the Chief of Staff card look the same as before.

## Non-goals

- The Writing tickets cards' layout and titles (WISE-430).
- The button's icon, label or copy behavior.
- Any other change to the card head grid or the owner avatar.

## Calls I made

- The ticket says "Epic cards" are untouched; the only other `rowHead` caller with an id is the Done card (`renderMerged`), which has no button. I read that as the card the ticket meant, and it stays as is.
- I move `extra` in `rowHead` rather than adding a new slot, since only ticket cards pass one. If a later caller wants something after the title, it can add a slot then.
- The title spans the full row instead of column 1 only, since nothing else shares its row now.
- Column 1 changes from `minmax(0, max-content)` to `max-content`. A ticket number never needs to shrink, and a shrinking column could let a narrow card squeeze the button.
