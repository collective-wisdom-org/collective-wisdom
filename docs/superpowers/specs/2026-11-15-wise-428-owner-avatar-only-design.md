# WISE-428: Show only the owner avatar on dashboard cards, pinned to the right edge

**Status:** Draft
**Ticket:** [#428](https://github.com/collective-wisdom-org/collective-wisdom/issues/428)

## Goal

The owner badge on a dashboard card shows only the avatar, gives the login on hover, and sits at the card's right edge on every card, so the avatars line up.

## Today

Facts from main at `a1ab8ed`, `agent-team/scripts/dashboard/page/`.

- `app.js` `ownerBadge(login)` renders `<span class="owner" title="<login>">`, then the `.avatar` (initial under an `<img alt="">`, both inside `aria-hidden="true"`), then a visible `<span class="login">`.
- `rowHead` puts the id, the title, the copy button and the badge in one `.head` div. It is used by Status and Backlog cards (`ticket()`) and Done cards (`renderMerged()`).
- `index.html`: `.head:has(> .id)` is a grid with `grid-template-columns: minmax(0, max-content) auto` and `justify-content: start`. The id and `.owner` both sit in row 1 spanning `1 / -1`; the title and copy button fall into row 2. With `justify-content: start` the grid is only as wide as its columns, so `justify-self: end` on `.owner` ends it at the title's width, not at the card's edge.
- `.owner .login` is the only CSS for the login text.

## Design

### Badge (`app.js`)

- `ownerBadge(login)` drops the `<span class="login">`. The rest stays: the `title` attribute (hover tooltip), the initial under the image, the lazy image from `avatars.githubusercontent.com`.
- The `.owner` span gets `role="img"` and `aria-label="<login>"`, escaped like the `title`. The avatar inside stays `aria-hidden`, so assistive tech reads the login once.
- No owner still renders nothing.

### Layout (`index.html`)

- `.head:has(> .id)` gets a third grid column, `minmax(0, max-content) auto 1fr`. The `1fr` column fills the rest of the card, so the grid spans the full card width; `justify-content: start` is no longer needed and goes.
- The title and copy button keep their columns in row 2, so the title wraps as it does now and the copy button stays beside it. `.owner` still spans `1 / -1` in row 1 with `justify-self: end`, which now means the card's right edge.
- The title is in row 2 and the avatar in row 1, so a long title never runs under the avatar.
- Drop the `.owner .login` rule. `.owner` keeps its size and colour rules; its `gap` and `max-width` (there for the login text) go.
- The Chief of Staff card head (`.cos-card .head`, no `.id`) is not touched.

### Tests (`app.test.js`)

- Extend the existing owner test: the badge has no `class="login"`, carries `title` and `aria-label` with the escaped login. Layout is CSS and gets no test, per `AGENTS.md` § Testing.

## Acceptance

- Every card with an owner shows only the avatar, no login text.
- Hovering the avatar shows the login.
- On the Done tab, avatars of all cards end at the same right edge whatever the title length; the same on Status and Backlog cards.
- Long titles still wrap and stay clear of the avatar.
- Cards with no owner look as before.
- A failed avatar image still shows the initial.

## Non-goals

- The avatar's size or shape.
- Any change to who counts as owner, or to the Agents rule from WISE-424.

## Calls I made

- The accessible name is `role="img"` plus `aria-label` on `.owner`. A plain `aria-label` on a span is ignored by some screen readers, and `role="img"` is the usual way to name an avatar.
- The grid gains a `1fr` third column instead of `width: 100%` plus `justify-content: start`, so the title column still shrinks to the title and the copy button stays next to it.
- The `title` attribute is kept as the tooltip. No custom tooltip.
- Status, Backlog and Done cards all change, since they share `rowHead`.
