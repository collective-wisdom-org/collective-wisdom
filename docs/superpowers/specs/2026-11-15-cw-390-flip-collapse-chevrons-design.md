# CW-390: Flip the dashboard collapse chevrons the right way up

**Status:** Draft
**Ticket:** [#390](https://github.com/collective-wisdom-org/collective-wisdom/issues/390)
**Builds on:** CW-369 (PR #383, merged), which added the band header chevrons.

## Goal

Every collapsible section header on the dashboard shows the opposite chevron from today: a collapsed section points up and an open section points down.

## Today

Facts from main at `6f6bfe2`, `agent-team/scripts/dashboard/page/index.html`.

- Line 37: `summary::after` draws the chevron from a small box with right and bottom borders, `transform:rotate(45deg)` (points down), `vertical-align:.12em`, `transition:transform .15s`.
- Line 38: `details[open] > summary::after` sets `rotate(-135deg)` (points up) and `vertical-align:-.05em`.
- Lines 40-41 repeat the same pair on `summary.band-head > h2::after` for the top-level bands (CW-369).
- `app.js` (`renderStatus`, `renderChief`) only sets `open`; it draws no chevron and needs no change.

## Design

CSS only, in `index.html`. No markup, `app.js` or test changes.

- Lines 37 and 40 (collapsed): `rotate(-135deg)` and `vertical-align:-.05em`.
- Lines 38 and 41 (open): `rotate(45deg)` and `vertical-align:.12em`.

The two `vertical-align` values move with the rotation they were tuned for: today's down chevron sits at `.12em`, the up one at `-.05em`, so the same shape keeps the same baseline after the swap. The box borders, size, margin and the `transition` stay, so the chevron still turns 180 degrees when a section opens or closes. `currentColor` keeps it right in light and dark mode with no extra rules.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/index.html` | Swap the rotation and `vertical-align` between the collapsed and open rules, for both the group summaries and the band headers. |

No new test: this is styling (`AGENTS.md` § Testing). The PR's proof is screenshots of a collapsed and an open section (group and band) in light and dark mode.

## Non-goals

- Moving the chevron to the left of the title, or changing its size or colour.
- A right-pointing collapsed chevron (the disclosure-triangle convention).

## Calls I made

- **Collapsed points up, open points down.** The ticket says to swap the two rotations, so that is what this builds. A right-pointing collapsed chevron is the other common convention; it is not what the ticket asked for.
- **The `vertical-align` values swap along with the rotations** rather than being retuned, because each was set for its shape. If the proof screenshots show the chevron off the baseline I tune it in the build and say so in `Differs from spec`.
- **No test.** Four CSS values change; nothing a test could catch would hurt users silently.
