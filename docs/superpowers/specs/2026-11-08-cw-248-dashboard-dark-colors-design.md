# CW-248: Match the dashboard dark colors to T3 Code dark

**Status:** Shipped
**Shipped:** in PR #250, as specified
**Ticket:** [#248](https://github.com/collective-wisdom-org/collective-wisdom/issues/248)

## Goal

In dark mode the dashboard uses the same black and near-black greys as T3 Code's dark theme, so it no longer looks navy beside the chat. Text, badges and the merge, build and error cards stay readable. Light mode does not change.

## T3 Code's dark colors (read from the app)

Read on 2026-11-08 from the CSS shipped in `/Applications/T3 Code (Beta).app` (`app.asar`, `apps/server/dist/client/assets/main-Du54ges0.css`), the `:root:is(.dark, .dark *)` rules. This machine has no custom T3 theme set (local storage holds only `t3code:theme-appearance-mode` = `system`), so the default dark theme is the one in use.

| T3 variable | T3 value | sRGB |
|---|---|---|
| `--background` | `#000` | `#000000` |
| `--card` | `#111` (newer rule: neutral-950 mixed 97% with white, about the same) | `#111111` |
| `--foreground` | `--color-neutral-100`, `oklch(97% 0 0)` | `#f5f5f5` |
| `--muted-foreground` | `--color-neutral-400`, `oklch(70.8% 0 0)` | `#a1a1a1` |
| `--border` | white at 8% | `#ffffff14` |

## Design

Only the dark half of each `light-dark()` pair in `agent-team/scripts/dashboard/page/index.html` `:root` changes. The light half of every pair stays byte for byte. No other line of the page changes.

| Variable | Dark today | Dark after | Why |
|---|---|---|---|
| `--bg` | `#0d1117` | `#000000` | T3 background |
| `--card` | `#161b22` | `#111111` | T3 card |
| `--fg` | `#e6edf3` | `#f5f5f5` | T3 foreground |
| `--muted` | `#9198a1` | `#a1a1a1` | T3 muted foreground |
| `--line` | `#30363d` | `#ffffff14` | T3 border, kept translucent as T3 has it |
| `--b-neutral` | `#30363d` | `#262626` | neutral-800, a solid grey pill on the card |
| `--b-neutral-fg` | `#c9d1d9` | `#d4d4d4` | neutral-300, drops the blue cast |
| `--tint-merge` | `#2a1316` | `#2d1918` | 12% `--edge-merge` over `#111` |
| `--tint-build` | `#261f10` | `#282113` | 12% `--edge-build` over `#111` |
| `--err-bg` | `#2d1214` | `#241110` | 14% `--err` over `#000` |
| `--b-low` | `#12261e` | `#1d3420` | 18% `--b-low-fg` over `#111` |
| `--b-medium` | `#272115` | `#372e1a` | 18% `--b-medium-fg` over `#111` |
| `--b-high` | `#2d1214` | `#3c2422` | 18% `--b-high-fg` over `#111` |

Unchanged in dark: `--accent` `#58a6ff`, `--bar` `#3fb950`, `--run` `#d29922`, `--err` `#ff7b72`, `--edge-merge`, `--edge-build`, and the badge text colors `--b-low-fg`, `--b-medium-fg`, `--b-high-fg`. Each is brighter against black than against navy.

Each tint is the hex of its color mixed into the surface it sits on, so it carries no blue from the old background. The values are fixed hex, not `color-mix()`, so the list reads the same way it does today.

### Contrast (WCAG ratio, dark mode, after)

| Pair | Ratio |
|---|---|
| text on background / card | 19.3 / 17.3 |
| muted on background / card | 8.1 / 7.3 |
| muted on merge tint / build tint | 6.4 / 6.2 |
| link on card / merge tint / build tint | 7.5 / 6.6 / 6.3 |
| error text on error box | 7.2 |
| low / medium / high badge | 7.0 / 6.9 / 5.7 |
| neutral pill | 10.2 |
| running and progress colors on card | 7.5 / 7.4 |

Every pair clears 4.5:1. For comparison, muted on the build tint is 5.6 today.

## Calls I made (surprising first)

- **The border stays translucent (`#ffffff14`), as T3 has it.** It is the only alpha value in the list. It reads as `#141414` on the background and about `#242424` on a card, which is how T3's borders look. A single solid grey would be too faint on cards or too strong on the background.
- **The link color stays GitHub blue (`#58a6ff`), not T3's primary blue.** T3's primary (`oklch(57.1% .21 264)`) is a button fill: as text it is 4.5:1 on black and 4.1:1 on a card, below the 7.5:1 the current link gets. The ticket asks to keep the accent readable, and the current one already is.
- **Badge backgrounds got a little stronger (18% of the badge text color, up from roughly 10 to 15% today).** On black the old strength made the pills hard to see against the card.
- **T3's default dark theme, not a custom one.** T3 lets you pick or edit themes (`data-theme-id`). None is set on this machine, so the dashboard matches the default. A custom T3 theme would not be followed; that is the same limit as CW-242, which follows macOS, not T3.
- **Hex values over `color-mix()`.** Same look, and the list stays one flat set of hex pairs that can be read at a glance.

## Tests

None. This changes color values only, which `AGENTS.md` § Testing says not to test. The existing suites must still pass: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.

Proved in the PR by a computed diff of `index.html` (only dark halves changed, light halves identical) and the contrast ratios above. Screenshots beside T3 Code could not be attached, so the PR lists them under Not proven.

## Docs

Nothing. No doc names the dark palette.

## Non-goals

- Light mode colors.
- Following the T3 Code theme setting or a custom T3 theme (CW-242 follows macOS).
- Changing the accent or status colors.
