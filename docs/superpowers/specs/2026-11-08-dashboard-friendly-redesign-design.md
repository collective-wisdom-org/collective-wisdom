# Dashboard redesign: one headline per ticket

**Status:** Shipped
**Shipped:** in PR #267, with differences: [as-built](../as-built/2026-11-08-cw-266-dashboard-friendly-redesign-as-built.md)
**Ticket:** [#266](https://github.com/collective-wisdom-org/collective-wisdom/issues/266)
**Follows:** CW-195 (layout overhaul), CW-240 (Details section), CW-242 and CW-248 (dark mode and T3 colours).

## Intent

The dashboard (`agent-team/scripts/dashboard/page/`) should read like a product someone keeps open all day, not a developer's debug view. Today every ticket shows seven small things at equal weight: id, stage badge, risk badge, Spec, PR, Copy thread link, the agent's status text, plus two disclosure triangles. Headings are bold text over hairlines, controls are grey outline buttons, and the page borrows GitHub's badge idiom everywhere. The fix is hierarchy and plain words: each ticket gets one headline (its title), one sentence saying where it is and what it needs, one action where it needs the user, and everything else quiet or behind a click.

Noah's words: "cleaner and more modern", "very developer-coded now and not actually a friendly UI". Noah picked this approach over a polish pass and an app shell.

## Goals

- Someone glancing at the page sees in one second what needs them and what is moving, without reading badges.
- Every ticket reads top to bottom: title, status sentence in plain words, one action, then the rest.
- Section and group names are plain words a non-developer would use.
- The page looks calm: one accent colour for attention, red only for blocked and errors, few borders, more air.
- Light and dark both look finished; dark keeps the T3 Code dark values from CW-248.
- Still fits a 300 to 400px side pane; wide windows get a multi-column grid as today.

## Non-goals

- No new data, API fields or server changes. `api.ts`, `merged.ts`, `server.ts`, the status groups in `groups.ts` and the state scripts do not change.
- No change to what the Chief of Staff writes into a ticket's `status` line.
- No change to the status-pane mod or the agent-gantt mod.

## Anti-goals

- A new dependency, build step, web font, icon font or image. The CSP stays `default-src 'self'; style-src 'self' 'unsafe-inline'`.
- Hiding data that is there today. Everything still reachable, some of it one click deeper.
- Animation beyond a hover or focus transition.
- A theme toggle or a settings panel.

## Constraints

- Dependencies identical: one `index.html` with inline CSS, one `app.js` ES module, tests in `app.test.js` run with `node --test`. No framework.
- The render functions stay pure and Node-testable. The browser shell (the part under `if (typeof document !== 'undefined')`) keeps working with the selectors it uses today: `details.chart`, `details.info`, `details.group[data-group]`, `.chart-body[data-ticket|data-merged|data-pm|data-chief]`, `.info-body[data-ticket|data-merged]`, `button[data-copy]`, `button[data-page]`, `button[data-pm-page]`, `button[data-tab]`, `#status`, `#merged`, `#cos`, `#cta`, `#error`. Markup inside those may change; the hooks keep their names.
- `data-group` keeps the API group name (for example `Awaiting merge approval`), so collapsed sections saved in localStorage by CW-200 keep working. Only the shown label changes.
- The 5 second poll must still keep open sections, a text selection, the copy button label and the Merged page, as today.
- Contrast: every text and background pair meets WCAG AA (4.5:1) in light and dark, checked with a one-off script and reported in the PR.
- Prose follows the `human-writing` skill: plain sentences, no em dashes.

## Approaches

Three were considered; Noah picked the second.

1. **Polish in place.** Keep every element, fix the system: type scale, spacing, softer colours, fewer badge colours, better tabs. Cheapest and lowest risk, but the page still reads as a list of labelled facts.
2. **Rebuild the ticket around one headline** (chosen). Title first, id muted, one plain sentence of status, one action where it needs the user, the rest quiet or behind a click. Sections and groups renamed to plain words. Same markup shape and render functions, bigger CSS and copy change. Picked because the friendliness problem is mostly equal weight on too many facts; hierarchy fixes that without new chrome.
3. **App shell.** Sidebar navigation, a summary strip with three big numbers, a content area. Looks most like a modern app in a wide window but fights the 300 to 400px pane, where the sidebar has to collapse anyway. Dropped.

## Design

### 1. Plain words everywhere

Two page-side maps in `app.js`, both exported and tested.

**Bands** (the three top-level sections from CW-195) are relabelled:

| Today | New label |
|---|---|
| Needs you | Your turn |
| In progress | In progress |
| Queued | Up next |

The Merged heading becomes **Done**.

**Groups** (API names, unchanged in `data-group` and in the API) get shown labels:

| API group name | Shown label |
|---|---|
| Awaiting merge approval | Ready to merge |
| Awaiting build approval | Spec ready to build |
| Awaiting teammate review | In review |
| Merging | Merging |
| Queued to merge | Waiting to merge |
| Speccing | Writing the spec |
| Building | Building |
| Queued to build | Waiting to build |
| Other | Blocked or waiting |

A group name the page does not know is shown as is.

**Status sentence** per stage, shown on every ticket as the line under the title:

| Stage | Sentence |
|---|---|
| awaiting-merge | Waiting for your merge approval |
| awaiting-build | Spec is waiting for your approval |
| blocked | Blocked. Needs an answer from you |
| awaiting-review | Waiting for a teammate's review |
| merge | Merging now |
| merge-queued | Waiting for a merge slot |
| spec | Writing the spec |
| spec-queued | Waiting for a spec slot |
| build | Building |
| build-queued | Waiting for a build slot |

A stage the page does not know shows the stage slug with hyphens turned to spaces, as `stageWords` does today. The sentence comes first; the agent-written `next` text (for example `awaiting-build since 14:40: spec at …`) stays, muted and smaller, under the sentence, clamped to two lines on the card with the full text in Details. Nothing is dropped.

### 2. The ticket card

Cards in Your turn and In progress. Up next is rows (section 3), so a blocked ticket, which sits in Up next under Blocked or waiting, is a row with the red left edge, the blocked sentence and the **Open issue** action. Top to bottom:

1. **Title**, semibold body size, wrapping. Falls back to the id when the title is empty.
2. **Meta line**, muted small: `CW-248 · low risk`. The id is a link to the issue. Risk is plain text, lowercased from the first word plus "risk" (`low risk`, `medium risk`, `high risk`); `not rated yet` shows as `not rated yet`. Only `high risk` is coloured (the red text token). No risk badge.
3. **Status sentence** (table above), body size, normal weight.
4. **Agent text** (`next`), muted small, two-line clamp.
5. **Footer row**: on the left a quiet summary `3 agents · 41m · $2.10` built from the Gantt data already summarised in `renderDetails` (agents count, active duration from `renderGantt`'s total, cost; parts missing are skipped; nothing when there is no Gantt). On the right the toggles **Agents** and **Details** as quiet text buttons (the existing `details > summary` elements) with a CSS chevron drawn with a border, no character glyphs or images. The Agents toggle keeps its task count pill.
6. **Action**, only in Your turn and for a blocked ticket: one filled accent button-styled link at the right of the meta line or below the status sentence (builder's call, must work at 300px). Ready to merge: **Open PR** (`prUrl`). Spec ready to build: **Open spec** (`specUrl`). Blocked: **Open issue** (`issueUrl`). When the url is missing or not http(s), no action is drawn. Elsewhere the Issue, Spec and PR links stay as quiet text in Details, plus a quiet **PR** text link on the card when there is one.

**Copy thread link** moves to Details as a small text button labelled **Copy thread link**, keeping `data-copy` and the Copied / Copy failed swap. It leaves the card face.

Card style: no border, card background token, 12px radius, 16px padding, 12px gap between cards. Your turn cards get a 3px left edge in the attention colour and a faint attention tint.  Hover lifts nothing; no shadows in dark mode, an optional very soft one in light (builder's call).

### 3. Rows (Up next and Done)

Flat rows as today, calmer: title first, then one muted line. Up next: `CW-251 · low risk · Waiting to build`. Done: `CW-248 · merged today 14:02 · $2.10 · 1.2M tokens`. The day word is `today`, `yesterday`, else `2026-11-06`, from an exported `dayWords(ms, now)` that is tested. Rows keep Agents and Details toggles as quiet text on that line's right. A thin divider between rows, no background.

### 4. Header and tabs

- Title **Agent team** stays, 22px semibold. Under it (or beside it when wide) one plain sentence replaces the three badges: `2 need you · 3 in progress · 1 waiting to build`, with the `need you` part in the attention colour and semibold when the count is above zero. When nothing needs the user: `Nothing needs you · 3 in progress`. `renderBadges` keeps its name and signature and returns this markup; its tests change.
- Tabs become a segmented control: a pill track in the card colour, the selected tab a filled white (light) or dark grey (dark) segment with a soft edge. Same `role=tab` markup and keyboard handling.
- Error line keeps `role="status"`, styled as a soft red banner with the red text token, hidden when empty.
- Band headings: small caps, muted, letter-spaced, with the count after them in the muted colour, no hairline. Group headings inside a band: body size semibold with the count pill; the summary row is the click target as today.

### 5. Chief of Staff tab

Same system: the Chief of Staff card gets the card style with the state as a coloured dot plus word (`● running`) instead of a badge; Project manager rows become rows as in section 3 with `Backlog ranking` or `Hygiene` as the title and `updated today 14:02` as the meta line. The **Thread** copy button becomes a quiet text button labelled **Copy thread link**.

### 6. Gantt

Structure, data and layout breakpoints from CW-195 stay. Styling only: track in the card colour with 6px radius, bars 6px radius, done bars the green token, running bars the attention colour, stale rows faded as today. Row names body size, numbers in tabular figures. The Total row semibold. Notes (`gnote`) stay.

### 7. Tokens

One token set at `:root` with `light-dark()`, as today. Palette, light then dark:

- Page `#fafafa` / `#000000`; card `#ffffff` / `#111111`; line `#e5e7eb` / `#ffffff14`.
- Text `#111827` / `#f5f5f5`; muted `#6b7280` / `#a1a1a1`.
- Accent (links, selected tab, action button) `#2563eb` / `#60a5fa`.
- Attention (Your turn edge and tint, `need you` count, running bars) `#b45309` / `#f59e0b`, tint `#fffbeb` / `#2a1f0a`.
- Red (blocked, high risk, errors) `#b91c1c` / `#f87171`, tint `#fef2f2` / `#2a1212`.
- Green (done bars, pass) `#15803d` / `#4ade80`.

The builder adjusts any value that fails AA and reports the ratios. The dark page and card values are the CW-248 ones and do not move.

Type: four sizes stay (22px title, 15px body, 13px small, 11px band label), system-ui. Line height 1.5. Spacing on a 4px scale.

### 8. Tests

`app.test.js` changes where markup changed on purpose, and adds one table-driven test each for: band and group labels (known name to label, unknown name as is, `data-group` keeps the API name), the status sentence map (known stage, unknown stage falls back to spaced slug), the action link (right url per stage, none without an http(s) url, none outside Your turn and blocked), `dayWords`, and the header sentence (zero, one and many, plural forms). The existing band order test stays. Test lines stay under the feature lines of the PR.

### 9. Screenshots

Before and after with the same `/api` snapshot at 360px and 1280px, light and dark, as CW-195 did: eight images in the PR, taken with headless Chrome from a throwaway script outside the repo.

## Left to the builder

- Exact placement of the action button (right of the meta line versus under the status sentence) as long as it works at 300px.
- The chevron CSS, the two-line clamp technique, the optional light-mode card shadow.
- How the footer summary is shared with `renderDetails` without duplicating the Gantt math.
- Any token nudge needed for AA.

## Calls I made

- **Plain-word labels live on the page, not in the API.** The group names are a contract the scripts and the status-pane mod share; relabelling on the page changes nothing downstream and keeps saved collapsed state valid.
- **Status sentence from the stage, not from the agent text.** The agent's `status` line is operational ("awaiting-build since 14:40: …"). A fixed sentence per stage is the only way to get consistent plain words without changing what agents write. The agent text stays underneath.
- **One attention colour (amber) for everything that needs the user; red only for blocked and errors.** CW-195 used red for merge approval to match its badge. Red reads as "something is wrong", and a ready-to-merge PR is good news. Amber says "your turn" without alarm.
- **Risk as text, not a badge; only high is coloured.** Three coloured pills per card was most of the noise. High risk is the one value that should catch the eye.
- **Copy thread link moves into Details.** It is used a few times a day, not at a glance.
- **Header badges become one sentence.** Three pills of different colours in the header were the loudest thing on the page.
- **Header counts follow the bands.** `need you` counts the Your turn band, `in progress` the In progress band, `waiting` the Up next band, minus blocked tickets, which get their own `1 blocked` in red when above zero. Zero counts are left out. This is a call, not something Noah specified.
- **Footer summary needs the Gantt's active time**, which `renderGantt` computes privately. The builder exports a small shared helper rather than recomputing it.
- **Relative day words in Done.** "merged today 14:02" is what a person would say.
