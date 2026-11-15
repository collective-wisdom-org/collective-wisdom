# CW-332: Show only the risk level on the dashboard badge and keep the reason in Details

**Status:** Shipped
**Shipped:** in PR #344, with differences: [as-built](../as-built/2026-11-14-cw-332-risk-badge-level-as-built.md)
**Ticket:** [#332](https://github.com/collective-wisdom-org/collective-wisdom/issues/332)
**Builds on:** PR #267 (CW-266, dashboard redesign). The build waits for #267 to merge.

## Goal

The risk on a dashboard ticket shows as one color-coded word, `Low`, `Medium` or `High`. The reason after the level (`docs only` in `Low (docs only)`) leaves the card and stays in the `Risk` row of Details.

## Today

Facts from PR #267's head (`e2eb56e`), since #267 rewrites the same card. `main` at `da765ee` still has the old badge.

- The Chief of Staff ends a status line with `Risk: <Level> (<reason>)`. `row()` in `agent-team/scripts/dashboard/groups.ts` puts everything after `Risk:` in `risk`, or `not rated yet`. `api.ts` passes it through.
- In #267, `ticket()` in `dashboard/page/app.js` builds a `meta` line used by cards and flat rows: `CW-248 · low risk · PR`. `riskText(risk)` reads the first word and returns `low risk`, `medium risk`, `high risk` or `not rated yet`. Only `high risk` is wrapped in `<span class="risk-high">` (red text). There is no risk badge.
- `riskClass()` is still defined in #267's `app.js` but nothing calls it.
- `renderDetails()` has a `Risk` row with the full `esc(r.risk)` text.
- #267's `index.html` has `--red`/`--red-tint`, `--green` and `--attn`/`--attn-tint` (amber, meaning "your turn"), and a `.badge` pill (`--soft` background, muted text). It has no yellow token and no green tint.
- `page/app.test.js` in #267 tests `riskText` with a table and asserts that only high risk is coloured.

So #267 already drops the reason from the card. What this ticket adds on top: a colored pill for all three levels, and the word alone (`Low`, not `low risk`).

## Design

1. **`riskLevel(risk)`**, exported from `app.js`, replaces `riskText` and the unused `riskClass`. It reads the first word of the trimmed text, case-insensitive, and returns `Low`, `Medium` or `High`, or `''` when the word is none of those.
2. **Meta line.** In `ticket()`, the risk item is:
   - with a level: `<span class="badge risk risk-low|medium|high">Low|Medium|High</span>`;
   - without one: `not rated yet` as plain muted text, as in #267.
   The reason never appears on the card. Cards and flat rows (Up next) share the meta line, so both get it.
3. **Colors** in `index.html`, light and dark through `light-dark()` like the other tokens:
   - Low: `--green` text on a new `--green-tint` (`#f0fdf4` / `#0f2a17`).
   - Medium: a new `--yellow` text token (`#a16207` / `#facc15`) on a new `--yellow-tint` (`#fefce8` / `#2a2410`).
   - High: `--red` on `--red-tint`.
   `.badge.risk-low|medium|high` set the background and color, font weight 600. The old `.risk-high` text rule goes.
4. **Details.** The `Risk` row keeps the full text (`Low (docs only)`). No change.
5. **Tests** in `page/app.test.js`, replacing #267's two risk tests:
   - One table over `riskLevel`: `Low (docs only)` → `Low`, `medium` → `Medium`, `HIGH: touches auth` → `High`, `not rated yet`, `''`, `unclear`, `undefined` → `''`.
   - One table over `renderStatus` for `Low (docs only)`, `Medium (x)`, `High (x)` and `not rated yet`: the meta line holds the badge with the right class and the level word only, the reason is not on the card, and `not rated yet` has no `risk-` class. The existing Details test already covers the full text in the `Risk` row.

## Leaves out

- The `Risk: <Level> (<reason>)` text the Chief of Staff writes, and the `status.md` table.
- `groups.ts` and `api.ts`: `risk` keeps the full text, which Details needs.
- `mods/agent-gantt`, which shows no risk.
- Any other part of #267's card.

## Calls I made (surprising first)

- **This undoes one #267 decision.** #267's spec says "Risk as text, not a badge; only high is coloured", because three colored pills per card were noise. This ticket asks for a green, yellow or red badge on every rated card, so low and medium get color again. I followed the ticket, as the newer ask.
- **Unrated means #267's `not rated yet`, not today's raw text.** The ticket says an unreadable level "keeps today's neutral badge and text". On top of #267 there is no neutral badge, so an unreadable level shows as #267 shows it: muted `not rated yet`. A risk text like `unclear (x)` therefore reads `not rated yet` on the card, and the raw text stays in Details.
- **New yellow token, not the amber attention color.** #267 uses amber for "needs you". Reusing it for Medium would make a Medium card look like it needs the user. `#a16207` on `#fefce8` is about 4.8:1 contrast; `#facc15` on `#2a2410` is higher.
- **Capitalized level word** (`Low`), as the ticket's acceptance writes it, not #267's lowercase `low risk`. The badge color carries the "risk" meaning; Details labels it `Risk`.
- **`riskClass` and `riskText` go.** One `riskLevel` gives both the class and the word, so there is one parser of the level.
- **Flat rows get the badge too**, since they share the meta line with cards.
