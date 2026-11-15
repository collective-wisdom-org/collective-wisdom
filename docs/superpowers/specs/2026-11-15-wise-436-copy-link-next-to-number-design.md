# WISE-436: Move the copy thread link control next to the ticket number on dashboard cards

**Status:** Draft
**Ticket:** [#436](https://github.com/collective-wisdom-org/collective-wisdom/issues/436)

## Goal

On a ticket card the copy thread link button sits right after the ticket number, on the number row, instead of after the title. On every card with a ticket number, the owner avatar gets its own column at the right edge, and the title wraps before that column instead of running under the avatar. The action links on cards waiting for your approval read `View PR` and `View spec` instead of `Open PR` and `Open spec`, since "Open" reads like acting on the PR or spec when the link only opens it.

## Today

Facts from main at `8c018e1`, `agent-team/scripts/dashboard/page/`.

- `app.js` `rowHead(idHtml, title, extra, ownerHtml)` renders `.head` as `.id`, `.title`, then `extra`, then the owner badge.
- Two callers pass an `.id`: `ticketRow` (Status and Backlog cards, and the `Ticket helper` card), whose `extra` is `copyButton(r.threadLink, { thread: true })`, and the Done cards in `renderMerged`, whose `extra` is `''`. Role cards and the Chief of Staff card build their own `.head` without `.id` and do not call `rowHead`.
- `copyButton` returns `''` when there is no thread link.
- `index.html`: `.head:has(> .id)` is a grid, `minmax(0, max-content) auto 1fr`. `.head .id` and `.owner` both span `1 / -1` in row 1, `.owner` with `justify-self: end`. The title and the button auto-place into row 2, columns 1 and 2, so the button follows the title.
- Because `.owner` shares the full-width row 1 and the title's column can grow to the card's full width, a long title runs to the card's right edge, right under the avatar (seen on a WISE-424 Done card).
- The action link labels come from `ACTIONS` in `app.js` (lines 117 and 118): `['awaiting-merge', ['Open PR', 'prUrl']]` and `['awaiting-build', ['Open spec', 'specUrl']]`. Every other place the dashboard uses those labels:
  - `app.js` line 370, the `ticketRow` doc comment (the `Open PR` or `Open spec` link).
  - `app.test.js` lines 136, 137 (the action table) and 145 (the rendered `>Open PR</a>` match).
  - `README.md` line 187, twice: "one link (`Open PR` or `Open spec`)" and "it is also the `Open spec` button".
  - Nothing else in `agent-team/`, `mods/`, `AGENTS.md` or `docs/agents/` uses them. Older specs under `docs/superpowers/` mention them as history and stay as written.
- `README.md` line 187 also describes the copy button as sitting with the title: "the ticket number ... above the title and a copy button with a thread glyph" and "A ticket's copy button is a small icon right after its title".

## Design

### Markup (`app.js`)

- `rowHead` renders `extra` right after the `.id` span and before the title: `.id`, `extra`, `.title`, owner badge. The doc comment says so.
- The `rowHead` signature and its callers stay the same. `ticketRow` is the only caller with a non-empty `extra`, so only ticket cards get the button move; Done cards render the same markup as before and change only through the CSS below.

### Layout (`index.html`)

- The `.head:has(> .id)` grid gets four columns, `max-content auto minmax(0, 1fr) auto`, and places the items explicitly instead of by auto-placement:
  - `.head .id`: column 1, row 1.
  - `.head > .copy-icon`: column 2, row 1.
  - `.owner`: column 4, row 1, the avatar's own column at the card's right edge. Its `grid-column: 1 / -1` and `justify-self: end` go.
  - `.head .title`: row 2, columns `1 / 4` (the first three), so it wraps at the start of the avatar's column, one column gap short of the avatar, and never runs under or up against it.
- Column 1 becomes `max-content` (the number never wraps, it is `white-space: nowrap` already), so the button sits right after the number whatever the title length or card width.
- With no thread link there is no button, column 2 is empty, and nothing follows the number.
- With no owner, column 4 is empty and zero wide, so the title wraps one column gap short of the right edge.
- The avatar column applies to every card with a ticket number: Status, Backlog, the `Ticket helper` card and Done cards.
- The `.head .copy-icon` top-margin nudge stays; check it still lines up with the number in the browser and drop or adjust it only if it no longer does.
- `.cos-card .head` and the role card head (no `.id`) are not touched.

### Action labels (`app.js`)

- `ACTIONS` maps `awaiting-merge` to `View PR` and `awaiting-build` to `View spec`. The URLs, the `action` class, `target="_blank"` and the rest of the middle row stay as they are.
- The `ticketRow` doc comment names the new labels.

### Docs (`README.md`)

- Line 187: `View PR` or `View spec` in the middle-row sentence, and "the `View spec` button" for the spec link.
- Line 187: the copy button sits right after the ticket number, and the title wraps before the avatar's column. Replace "A ticket's copy button is a small icon right after its title" with "right after its ticket number".

### Tests (`app.test.js`)

- Update the action table (lines 136, 137) and the rendered-link match (line 145) to `View PR` and `View spec`.
- Tighten the existing `threadLink becomes a copy button` test so it asserts the order: the `.id` span, then the button, then the `.title` span. Layout is CSS and gets no test, per `AGENTS.md` § Testing.

## Acceptance

- On a ticket card the button is directly right of the ticket number, on the same line, and the owner avatar stays pinned to the card's right edge.
- The title is on its own line below, with no button after it.
- On every card with a ticket number, Done cards included, a long title wraps before the avatar's column: no title text sits under or against the avatar.
- The `Ticket helper` card shows the button next to its label.
- A ticket with no thread link shows no button and no gap.
- A long title or a narrow card does not push the button off the number row.
- Role cards and the Chief of Staff card look the same as before. Done cards change only in where their title wraps.
- A card waiting on merge approval shows a `View PR` link, and one waiting on build approval shows `View spec`. No `Open PR` or `Open spec` text is left on the page or in `README.md`.

## Non-goals

- The Writing tickets cards' layout and titles (WISE-430).
- The copy button's icon, label or copy behavior.
- What the action links point at, or any other middle-row control (`Approve`, `Changes`, `Mark todo`).
- The avatar's size or shape, or any change to the owner badge markup.

## Calls I made

- The new label is `View spec`, lower case s, matching today's `Open spec` and the page's sentence-case labels (`Mark todo`, `Full backlog`). The request said `View Spec`; say so if the capital S is wanted.
- The README's copy-button sentences change in this PR too, since they describe the old place of the button.
- The avatar column covers Done cards too, not just the cards with the button: the user's example was a Done card, and all of these cards share one grid.
- The avatar stays on the number row and the title starts on the row below; the title just stops at the avatar's column. The avatar does not move down beside the title.
- A card with no owner keeps an empty avatar column, so its title wraps one column gap (`--s1`) short of the edge. Dropping that gap would need a second grid rule for cards without an owner, which isn't worth it for a few pixels.
- The ticket says "Epic cards" are untouched; the only other `rowHead` caller with an id is the Done card (`renderMerged`), which has no button. I read that as the card the ticket meant: it gets no button and keeps its markup, and only the avatar column change reaches it.
- I move `extra` in `rowHead` rather than adding a new slot, since only ticket cards pass one. If a later caller wants something after the title, it can add a slot then.
- Column 1 changes from `minmax(0, max-content)` to `max-content`. A ticket number never needs to shrink, and a shrinking column could let a narrow card squeeze the button.
