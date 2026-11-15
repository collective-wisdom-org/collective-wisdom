# CW-370: Show every dashboard row as a card

**Status:** Shipped
**Shipped:** in PR #389, as specified (no screenshots; see the PR's Not proven)
**Ticket:** [#370](https://github.com/collective-wisdom-org/collective-wisdom/issues/370)
**Overlaps:** CW-349, CW-350, CW-354, CW-357 and CW-369 edit the same row markup or `renderStatus`. Whoever builds second rebases on the others.

## Goal

Every ticket row and project manager row on the dashboard is the same rounded card, in every section on both tabs. No section is a plain list with divider lines.

## Today

Facts from main at `90d7a68`, `agent-team/scripts/dashboard/page/`.

- `ticket()` in `app.js` draws a live card as `li.ticket` (Your turn, In progress) and a flat row as `li.row` (Up next and Not started, the `flat: true` bands). `renderStatus` wraps them in `ul.cards` or `ul.rows`.
- A flat row is "compact": a title and one footer with the Agents and Details control and the meta line. A blocked flat row is not compact; it is laid out like a card and gets `li.row.blocked`.
- `renderMerged` (Done) and `teamList` (project manager rows on the Chief of Staff tab) draw `ul.rows > li.row`.
- In `index.html`, `.ticket` is the panel (`--card` background, 12px radius, `--s4` padding, shadow, `--s1` gap) and `ul.cards` is the grid (`auto-fill`, `minmax(min(100%, 22rem), 1fr)`). `ul.rows > li.row` is padding plus a `border-top` divider; `li.row.blocked` adds the red tint, inset red edge and radius.
- Nothing in the browser shell selects `li.row` or `ul.rows`; it finds rows by `data-ticket`, `data-merged` and the `.seg` buttons.

## Design

### Markup (`app.js`)

1. `ticket()` gives every row `li.ticket`. A compact row adds `compact`, a blocked flat row adds `blocked`, Your turn keeps `attn`. So the classes are `ticket`, `ticket attn`, `ticket compact` and `ticket blocked`. The content of each row stays exactly as today; only the class changes.
2. `renderStatus` wraps every band in `ul.cards`.
3. `renderMerged` and `teamList` draw `<ul class="cards">` with `<li class="ticket compact">`. Content unchanged.
4. Doc comments that say "flat row (`li.row`)" are updated to match.

### CSS (`index.html`)

1. Remove `ul.rows > li.row`, `ul.rows > li.row:first-child`, and the `li.row .head + .meta` half of the `.cos-card .meta` selector.
2. `ul.rows > li.row.blocked` becomes `.ticket.blocked { background:var(--red-tint); box-shadow:inset 3px 0 0 var(--red), 0 1px 2px var(--shadow); }`, the same shape as `.ticket.attn`. `li.blocked .status` stays.
3. No `compact` rule is needed: the `.ticket` gap and the `.foot` top margin already space a title and footer. The class is there so a later tweak has a hook.

### Phone width

`ul.cards` already collapses to one column below 22rem plus gutters, so every section becomes a single stack of full-width cards on a phone, as Your turn does today.

### Not started in the grid

Not started rows are slim (id only) and sit in the same grid, so on a wide screen they show as several short cards per line. That reads as a set of chips rather than a list. I keep it, per the ticket's assumption,. The PR could not show it (no screenshots), so it is listed under Not proven.

## Test

One table-driven test in `app.test.js`: for each section (Your turn, In progress, Up next, Not started from `renderStatus`; Done from `renderMerged`; project manager from `renderChief`), the rows come out as `li.ticket` inside `ul.cards`, and the html has no `li class="row"` or `ul class="rows"`. A blocked Up next row has `ticket blocked`, a Your turn row has `ticket attn`. The existing merged pager test that counts `<li class="row">` changes to count the new class.

The panels, copy icon, pager and 5-second redraw are unchanged code; the existing tests cover them. The PR proof is the markup test and a grep. Screenshots of both tabs in light and dark, at desktop and phone width, were not taken, and the PR lists them under Not proven.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `ticket()`, `renderStatus`, `renderMerged`, `teamList` draw `ul.cards > li.ticket`. |
| `agent-team/scripts/dashboard/page/index.html` | Drop the row and divider rules; `.ticket.blocked` replaces `li.row.blocked`. |
| `agent-team/scripts/dashboard/page/app.test.js` | The markup test; the pager count update. |

## Non-goals

- What a row shows (title, ids, links, meta line, "since" text).
- The Chief of Staff card, the Agents/Details switch, the gantt.
- Moving Done to its own tab (CW-350), pagination (CW-349), collapsible headers (CW-369).

## Calls I made

- **Up next, Done and the project manager list go into the multi-column grid.** On a wide screen they show two or three cards per line instead of one list. The ticket assumed this; the other choice was a one-column stack of cards.
- **Not started's id-only rows are short cards in the same grid.** They look like chips on a wide screen. Kept per the ticket; listed under Not proven in the PR.
- **One class, `ticket`, for every row, with `compact` and `blocked` modifiers,** instead of keeping `row` and styling it like a card. Then there is one card rule and nothing left named `row`.
- **The blocked tint keeps the card shadow** (`inset` red edge plus the drop shadow), the same way `.ticket.attn` does.
- **A live card that is blocked gets no `blocked` class**, as today: only flat rows were marked blocked, and the ticket doesn't ask to change that.
- **No CSS for `compact`.** The existing card gap and footer margin space it; the class is only a hook.
