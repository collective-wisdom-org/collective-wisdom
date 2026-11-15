# CW-266: A friendly dashboard, one headline per ticket

**Status:** Shipped
**Shipped:** in PR #340, with differences: [as-built](../as-built/2026-11-14-cw-266-friendly-dashboard-as-built.md)
**Ticket:** [#266](https://github.com/collective-wisdom-org/collective-wisdom/issues/266)
**Replaces:** PR #267 (Noah's first build of this ticket, on `feat/cw-266-dashboard-friendly-redesign`). Its design doc, `docs/superpowers/specs/2026-11-08-dashboard-friendly-redesign-design.md`, lives only on that branch; this spec carries its design over and adapts it to today's main.

## Goal

The dashboard (`agent-team/scripts/dashboard/page/`) reads like a product someone keeps open all day, not a debug view. Each ticket gets one headline (its title), one plain sentence saying where it stands, at most one action where it needs the user, and everything else quiet or one click deeper.

Noah's words from #267's design: "cleaner and more modern", "very developer-coded now and not actually a friendly UI". The approach (rebuild the ticket around one headline, rather than a polish pass or an app shell) is the one Noah picked there and the repo owner approved on #267.

## Starting point: rebuild on main, porting #267 by hand

#267 is approved and green but was cut from main on 2026-11-08. Since then six PRs changed the same three page files, and a test merge conflicts in all three (`app.js`, `app.test.js`, `index.html`):

- CW-260 and CW-286: ticket helper rows (a placeholder `Writing tickets` group, helper sessions in the charts).
- CW-296: a fourth band, `Not started`, with `Todo` and `Backlog` groups and a `Full backlog` link.
- CW-307: the copy icon right after each ticket title (replaced the `Copy thread link` text button).
- CW-324: the stage and its start time (`build since 14:02`) on every card.
- CW-334 (merged as #335): issue and backlog links for Linear and Jira. It changed `api.ts`, `merged.ts` and `server.ts`, not the page, so it only matters here as the source of `issueUrl` and `moreUrl`.

So the build starts from current main and ports #267's pieces by hand rather than rebasing or cherry-picking its commits. The parts that carry over nearly as written: the label and sentence maps (`groupLabel`, `stageSentence`), `riskText`, `dayWords`, `actionFor`, the header sentence in `renderBadges`, the footer summary, the token set and most of the CSS, and their tests. The `ticket()`, `renderStatus`, `renderMerged` and `renderChief` markup is rewritten against main's versions so the features above keep working.

**CW-332** (risk badge shows only the level, reason in Details) is open and in progress, and its ticket says to build on top of #266 once it merges. This spec already shows only the level on the card and keeps the full text in Details, in the level's colour, so CW-332's acceptance holds with risk as coloured text instead of a pill (see Calls I made). If CW-332's PR merges first, the build rebases onto it and keeps its tests passing where the markup allows.

## Non-goals

- No new data, API fields or server changes. `api.ts`, `groups.ts`, `merged.ts`, `server.ts` and the state scripts do not change.
- No change to what the Chief of Staff writes into a ticket's `status` line.
- No change to the status-pane or agent-gantt mods.
- #260's helpers on the Chief of Staff tab keep their behaviour; only their styling follows the new system.

## Anti-goals

- A new dependency, build step, web font, icon font or image. The CSP stays as it is.
- Hiding data that is there today. Everything stays reachable, some of it one click deeper.
- Animation beyond a hover or focus transition. A theme toggle or settings panel.

## Constraints

- One `index.html` with inline CSS, one `app.js` ES module, tests in `app.test.js` under `node --test`. No framework.
- Render functions stay pure and Node-testable. The browser shell (under `if (typeof document !== 'undefined')`) keeps working with the hooks it uses today: `details.chart`, `details.info`, `details.group[data-group]`, `.chart-body[data-ticket|data-merged|data-pm|data-chief]`, `.info-body[data-ticket|data-merged]`, `button[data-copy]` (including the icon variant from CW-307), `button[data-page]`, `button[data-pm-page]`, `button[data-tab]`, `#status`, `#merged`, `#cos`, `#cta`, `#error`. Markup inside them may change; the hooks keep their names.
- `data-group` keeps the API group name, so collapsed sections saved in localStorage keep working. Only the shown label changes.
- The 5 second poll still keeps open Agents and Details sections, a text selection, the copy button state and the Merged page.
- Every text and background pair meets WCAG AA (4.5:1) in light and dark, checked with a one-off script outside the repo and reported in the PR.
- Fits a 360px pane with no sideways scroll; wide windows keep a multi-column card grid.
- Prose follows the `human-writing` skill.

## Design

### 1. Plain words

**Bands:** `Needs you` becomes **Your turn**, `In progress` stays, `Queued` becomes **Up next**, `Not started` stays. The `Merged` heading becomes **Done**.

**Group labels** (page only; `data-group` and the API keep the name):

| API group | Shown label |
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
| Writing tickets | Writing tickets |
| Todo | To do |
| Backlog | Backlog |

An unknown group name shows as is.

**Status sentence** per stage, the line under the title:

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

An unknown stage shows its slug with hyphens as spaces, as `stageWords` does. When `stageAt` parses, the sentence ends with ` since HH:MM` (CW-324's time, kept). A row with no stage (helpers, Todo, Backlog) has no sentence.

### 2. The ticket card (Your turn, In progress)

Top to bottom:

1. **Title**, semibold, wrapping, followed by the CW-307 copy icon when there is a `threadLink`. Falls back to the id when the title is empty. A helper row shows its request as the title, as today.
2. **Meta line**, muted small: `CW-248 · Low risk · PR`. The id links to the issue (`issueUrl`, so Linear and Jira work per CW-334). Risk is the level word only (`Low risk`, `Medium risk`, `High risk`) in the level's text colour (green, amber, red); a risk text with no readable level shows as is, muted (`not rated yet`). An empty risk (helpers) shows nothing. `PR` is a quiet link when there is a `prUrl`. A helper's meta line reads `Ticket helper`.
3. **Status sentence**, body size.
4. **Agent text** (`next`), muted small, clamped to two lines; the full text stays in Details.
5. **Action**, only for `awaiting-merge` (**Open PR**), `awaiting-build` (**Open spec**) and `blocked` (**Open issue**), as one filled accent link under the status sentence. No action when the url is missing or not http(s).
6. **Footer**: a quiet summary `3 agents · 41m 05s · $2.10` from the Gantt data (parts missing are skipped, nothing without a Gantt), then the **Agents** (with its task pill) and **Details** toggles as quiet text with a CSS chevron. Helpers keep no Details, as today.

Card style: no border, card background, 12px radius, 16px padding. Your turn cards get a 3px left edge in the attention colour and a faint attention tint. Details keeps the Issue, Spec and PR links, the stage, the full risk text and the agent text.

### 3. Rows (Up next, Not started, Done)

Flat rows, title first, then one muted meta line, with the Agents and Details toggles on that line's right; a thin divider between rows.

- Up next: `CW-251 · Low risk · Waiting to build`. A blocked ticket keeps its red left edge, uses the blocked sentence, and gets the **Open issue** action.
- Not started: `CW-251` only; the Backlog group keeps its `Full backlog` link.
- Done: `CW-248 · merged today 14:02 · $2.10 · 1.2M tokens · PR`. The day word is `today`, `yesterday` or `2026-11-06`, from an exported `dayWords(ms, now)`. The Spec link moves into Details.

### 4. Header and tabs

- `Agent team` stays. The three badges become one sentence from `renderBadges` (same name and signature): `2 need you · 3 in progress · 1 waiting · 1 blocked`. `need you` is the Your turn count, in the attention colour and semibold; `in progress` the In progress band; `waiting` the Up next band minus blocked tickets; `blocked` in red. Zero counts are left out; with nothing for the user it starts `Nothing needs you`. Not started is not counted.
- Tabs become a segmented control with the same `role=tab` markup and keyboard handling.
- The error line keeps `role="status"`, as a soft red banner, hidden when empty.
- Band headings: small, muted, letter-spaced. Group headings: body size semibold with the count pill.

### 5. Chief of Staff tab

The Chief of Staff card takes the card style, with its state as a coloured dot and word (`● running`) instead of a badge. Project manager rows become rows as in section 3 (`Backlog ranking` or `Hygiene` as the title, `updated today 14:02` as the meta line). The `Thread` text button becomes the CW-307 copy icon, so the page has one copy control style.

### 6. Gantt

Data, structure and breakpoints stay. Styling only: track in the card colour, 6px radius bars, done bars green, running bars and the running CI wait in the attention colour, stale rows faded, numbers in tabular figures.

### 7. Tokens

One set at `:root` with `light-dark()`, light then dark, from #267:

- Page `#fafafa` / `#000000`; card `#ffffff` / `#111111`; line `#e5e7eb` / `#ffffff14`.
- Text `#111827` / `#f5f5f5`; muted `#636a77` / `#a1a1a1`.
- Accent `#2563eb` / `#60a5fa`.
- Attention `#b45309` / `#f59e0b`, tint `#fffbeb` / `#2a1f0a`.
- Red `#b91c1c` / `#f87171`, tint `#fef2f2` / `#2a1212`.
- Green `#15803d` / `#4ade80`.

The dark page and card values are CW-248's and do not move. The builder nudges any value that fails AA and reports the ratios. Type: 22px title, 15px body, 13px small, 11px band label, system-ui, line height 1.5, 4px spacing scale.

### 8. Tests

`app.test.js` changes where the markup changes on purpose, and gets one table-driven test each for: group and band labels (known, unknown as is, `data-group` keeps the API name), the status sentence (known stage, unknown slug, the `since` time), risk text (three levels, unreadable as is, empty), the action (right url per stage, none without an http(s) url, none for other stages), `dayWords`, and the header sentence (zero, one, many, blocked apart). The band order, helper, Not started, copy icon and Full backlog tests keep passing, edited only for markup. Test lines stay under the feature lines.

## Proof for the PR

- The contrast script's result for every pair, light and dark.
- Screenshots from headless Chrome of the same `/api` snapshot at 360px and 1280px, light and dark, attached if the PR can carry images, else listed under Not proven.
- Both test commands from `AGENTS.md` (pytest and the dashboard `node --test` line).

## Calls I made

- **Rebuild on main and port #267 by hand, not rebase it.** All three page files conflict, and six features landed on them since #267 was cut. Porting the helpers and CSS keeps Noah's work where it still fits and avoids a conflict resolution that silently drops one of those features.
- **The copy icon stays on the card face, after the title.** #267's design moved `Copy thread link` into Details. CW-307 merged after that design and put a copy icon after the title on purpose, so this keeps CW-307. The Chief of Staff tab's `Thread` button uses the same icon.
- **Risk is the level word in its colour, not a pill, and not only high in colour.** #267 coloured only high risk. CW-332 asks for a colour-coded level word with the reason in Details. Coloured text keeps the card calm and still meets CW-332, so CW-332 may close as covered or shrink to whatever is left.
- **CW-324's `since HH:MM` joins the status sentence** (`Building since 14:02`) instead of being dropped.
- **Labels for main's newer groups:** `Todo` shows as `To do`; `Writing tickets` and `Backlog` keep their names. `Not started` keeps its band name.
- **The header sentence leaves out Not started.** Those tickets are not active; counting them would make the header noisy.
- **Done rows move the Spec link into Details**, so the meta line keeps one link (PR).
- **No muted count after band headings and the existing duration format in the footer**, as #267 shipped (its as-built), since the header already gives the counts.
- **Light muted gray `#636a77`**, the value #267 nudged to from `#6b7280` to pass AA.
- **#267 stays open** until this PR merges; the PR description names it so the user can close it.
