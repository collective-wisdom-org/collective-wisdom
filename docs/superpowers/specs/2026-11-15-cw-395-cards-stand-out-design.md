# CW-395: Make dashboard cards stand out a little more

**Status:** Shipped
**Shipped:** in PR #400, as specified
**Ticket:** [#395](https://github.com/collective-wisdom-org/collective-wisdom/issues/395)

## Goal

A dashboard card's edge is easy to see against the page in light and dark mode, without a heavy outline and without changing any other colors.

## Today

Facts from main at `6f6bfe2`, `agent-team/scripts/dashboard/page/index.html`.

- Page `--bg` is `#fafafa` light and `#000000` dark. Card `--card` is `#ffffff` light and `#111111` dark.
- Cards have no border. Their edge is `box-shadow: 0 1px 2px var(--shadow)`, with `--shadow` at `#0000000f` light and `transparent` dark. In dark mode there is no edge at all, only the gap between `#111111` and black.
- The card surfaces are `.ticket`, `.ticket.attn`, `.ticket.blocked` and `.cos-card`. The attn and blocked cards add an inset 3px colored left edge in the same `box-shadow` list.
- The active `.seg` and `.tabs` buttons also use `--card` and `--shadow`, but they sit on a `--soft` switch background, not on the page. `.track` uses `--card` as its background inside a card's gantt panel.

## Design

One new token and a hairline ring on the four card surfaces.

1. Add `--edge:light-dark(#00000014, #ffffff1a)` to `:root`: 8% black in light mode, 10% white in dark mode.
2. Add `0 0 0 1px var(--edge)` to the `box-shadow` of `.ticket`, `.ticket.attn`, `.ticket.blocked` and `.cos-card`, after the existing shadows. For attn and blocked the list becomes inset left edge, ring, drop shadow.

The ring is a box-shadow, not a `border`, so the card's size, padding and layout do not change and the inset left edge keeps drawing on top. In light mode the ring comes out close to `#e6e6e6` on the `#fafafa` page, about the shade of `--line`. In dark mode it is close to `#1a1a1a` around a `#111111` card on black: visible, still quiet.

Backgrounds do not change, so text contrast on cards stays exactly as today. The attn and blocked tints are untouched; the ring sits outside them.

### Left alone

- `--bg`, `--card` and `--shadow` keep their values.
- The active `.seg` and `.tabs` buttons keep their look. They sit on `--soft`, where white or `#111111` already separates, and a ring would make the switch look busier.
- `.track` is unchanged: it is not on the page background and the ticket does not ask for gantt changes.

## Test

Styling only, so no automated test, per `AGENTS.md` § Testing. The existing dashboard tests run to show nothing else broke. Screenshots of both themes are not something the build can take, so the PR lists the visual check under Not proven.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/index.html` | Add `--edge`; add the ring to the four card rules. |

## Non-goals

- A card redesign, new card colors, or new colors for other parts of the page.
- The tab and segment buttons, the gantt track.

## Calls I made

- **A hairline ring, not a token change.** Darkening the page or lightening the card would shift every surface that uses those tokens (buttons, track, tints). A ring touches only the cards.
- **The ring is a `box-shadow`, not a `border`,** so card size and layout stay pixel for pixel the same.
- **Dark mode gets an edge for the first time** (10% white). Today dark cards have none.
- **The active tab and segment buttons get no ring.** They sit on the grey switch, not the page.
- **`--shadow` stays as is,** including `transparent` in dark mode. The ring does the work.
- **Exact strengths (8% light, 10% dark) are my pick.** Easy to tune in review if they read too strong or too weak.
