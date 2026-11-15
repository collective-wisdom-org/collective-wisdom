# CW-345: One Agents and Details control on every row, and a waiting-time counter

**Status:** Shipped
**Shipped:** in PR #351, as specified
**Ticket:** [#345](https://github.com/collective-wisdom-org/collective-wisdom/issues/345)
**Builds on:** CW-266 (PR #340, merged), the redesign this keeps. CW-332 (PR #344, merged as `6e85821`), the risk pill, which this does not touch.

## Goal

Every row on the dashboard opens Agents and Details the same way, from the same spot, one panel at a time. A ticket waiting on someone (`awaiting-*`) shows how long it has waited, counting up live, instead of the Chief of Staff's long status line.

## Today

Facts from main at `6e85821`.

- `chartToggle(attr, id, gantt, open)` in `agent-team/scripts/dashboard/page/app.js` returns a `<details class="chart">` whose `<summary>` is `Agents <pill>`, or nothing when the Gantt has no tasks. Details is a second `<details class="info">`. Both sit inside `.foot`.
- Live cards (`ticket()`): the foot is the summary line (`3 agents · 41m 05s · $2.10`), then the two toggles. Flat rows (Up next, Not started, a blocked row is a card-like row): the foot is the meta line, then the toggles. Merged rows (`renderMerged`) build their own pair. Project-manager rows (`teamList`) have an Agents `<details data-pm>` on its own line, under the meta, and no Details. Ticket helper cards have Agents and no Details.
- `index.html`: `.foot .summary, .foot .meta { margin-right:auto }` pushes the toggles to the far right. `.foot > details[open] { flex:1 1 100%; order:3 }` makes an open `<details>` (its summary and its body together) jump to a new line below the foot.
- Open state: before a rebuild, `poll()` reads `details.chart[data-ticket][open]` and `details.info[data-ticket][open]` into two sets and passes them to `renderStatus`; `drawMerged` does the same with `data-merged`, `drawCos` with `details.chart[data-pm][open]`. The merged and pm lists are compared with every panel closed, so opening one is not a change.
- `draw()` runs every second. It patches chart bodies, rewrites a Details body only when its html changed, and refreshes `.summary[data-ticket]` text in place.
- Status: `stageSentence(stage, stageAt)` ends with ` since HH:MM` from `since()`. `ticket()` prints `r.next` (the status line before `Risk:`, cut in `groups.ts`) as `<p class="next">`, clamped to two lines. `renderDetails` already shows the full `next` in its `Next` row.

## The problems, and what fixes each

| # | Problem | Fix |
|---|---|---|
| 1 | The toggles sit at the far right, away from the title, and are easy to miss. | One labelled control, **Agents · Details**, is the first thing on the row's last line, at the left edge, under the text it belongs to. `margin-right:auto` goes. |
| 2 | Merged rows often show only Details, in another spot, because `chartToggle` drops Agents when there are no tasks. | Every ticket row draws both segments, always in the same order and place. With no tasks, Agents is drawn disabled (`Agents 0`), so Details never moves. |
| 3 | Both panels can be open at once and stack, and an open toggle jumps below its neighbour. | The control is two buttons in a fixed strip, and the panels live in one region under it. Opening one closes the other. The buttons never move. The pressed segment is joined to its panel. |
| 4 | Waiting tickets show a long status line and a static ` since HH:MM`. | `awaiting-*` cards show `waiting 3h 16m`, counting up from `stageAt`, in place of the `next` line. The full line stays in Details (`Next` row). |

## Approaches weighed

| Approach | For | Against | Verdict |
|---|---|---|---|
| **A. Segmented control on the row, one panel at a time** (Agents · Details as two buttons, panel under the row) | Small step from today. Panel stays next to its ticket. Several tickets can be open at once to compare. Same pattern fits cards, flat rows, merged rows and pm rows. Open state stays a per-row value, as today. | Panels are still as narrow as a card (22rem columns), as today. | **Chosen.** |
| B. ARIA tabs inside an opened row (Agents \| Details, one always selected) | Clear one-at-a-time. | A tablist needs one tab selected, so "both closed", the row's normal state, has no clean meaning; a third "closed" tab or a separate expand step adds a click. | Folded into A: same look, but as two disclosure buttons that can both be off. |
| C. Side panel or drawer opened by clicking the row | Wide room for the Gantt and spec text. | One ticket at a time. Covers part of the list it should sit beside. A dialog needs focus moves and a trap, a phone needs a full sheet, and the poll must refresh a second surface. Clicking the row clashes with the links and copy icon in it. Biggest change to the CW-266 layout. | Not now. A later ticket if the narrow panel proves a problem. |
| D. Modal or full-page ticket view | Most room. | Hides the live list, which is the point of keeping the page open. Full page needs routing and a back step. | Rejected. |
| E. Always-visible compact summaries with one "More" control | Fewer clicks for the common facts. | The summary line already does this on cards. "More" would open Agents and Details together, which is problem 3 again. Merged and pm rows have little to summarise. | Kept the part that exists (the summary line next to the control); rejected the single "More". |
| F. Plain labelled buttons next to the title | Very visible. | Titles wrap and carry the copy icon; buttons there crowd the headline CW-266 built the card around, and sit far from where the panel opens. | Kept "plain labelled buttons"; placed them on the foot line instead. |
| G. Keep `<details>`, add `name="..."` so the browser makes them exclusive | Least code. Keeps today's selectors. | The summary lives inside its `<details>`, so the open one still moves to the panel's line (today's jump). CSS cannot pull the summary back out reliably (`display:contents` on `<details>` is unreliable). | Rejected. |

## Design

### 1. The control

One helper, `panelSwitch(scope, id, { gantt, view, details })`, replaces `chartToggle` and the hand-built pairs. `scope` is `ticket`, `merged` or `pm`; `view` is `'agents'`, `'details'` or `''`; `details: false` drops the Details segment (pm rows only).

Markup for a ticket row with Agents open:

```html
<div class="foot">
  <div class="switch" role="group" aria-label="CW-341 panels">
    <button type="button" class="seg" data-ticket="CW-341" data-view="agents"
            id="seg-ticket-CW-341-agents" aria-expanded="true" aria-controls="pan-ticket-CW-341-agents">
      Agents <span class="pill">3</span></button>
    <button type="button" class="seg" data-ticket="CW-341" data-view="details"
            id="seg-ticket-CW-341-details" aria-expanded="false" aria-controls="pan-ticket-CW-341-details">
      Details</button>
  </div>
  <span class="summary" data-ticket="CW-341">3 agents · 41m 05s · $2.10</span>
</div>
<div class="panel" id="pan-ticket-CW-341-agents" role="region" aria-labelledby="seg-ticket-CW-341-agents">
  <div class="chart-body" data-ticket="CW-341"></div></div>
<div class="panel" id="pan-ticket-CW-341-details" role="region" aria-labelledby="seg-ticket-CW-341-details" hidden>
  <div class="info-body" data-ticket="CW-341">…</div></div>
```

- `data-ticket` becomes `data-merged` or `data-pm` by scope, as today. Every id and attribute value goes through `esc()`.
- The bodies keep their classes and data attributes (`.chart-body[data-*]`, `.info-body[data-*]`), so `drawCharts`, `draw()`'s `fill` and `patchChart` do not change.
- No Gantt tasks: the Agents button gets `disabled`, `title="No agent sessions recorded"`, pill `0`, and no Agents panel is drawn.
- Ticket helper cards: Details is drawn disabled (`title="No ticket yet"`), so the helper card's control matches the others.
- Project-manager rows: Agents only (`details: false`). They have no Details body, and making one is out of scope.

### 2. Where it sits

One rule for every row: the control is the first item on the row's last line (`.foot`), at the left edge. The line's text follows it.

| Row | `.foot` reads |
|---|---|
| Live card | control, then the summary line |
| Blocked row | control, then the summary line (it is laid out as a card) |
| Flat row (Up next, Not started) | control, then the meta line |
| Merged row | control, then the meta line (`CW-339 · merged today 13:10 · $1.20 · PR`) |
| Ticket helper card | control, then the summary line |
| Project-manager row | control, then the meta line (`● finished · updated today 09:12`); the pm meta moves from its own line into the foot |

Panels come after `.foot`, inside the `li`, at full row width.

### 3. Look

Built from the existing tokens and the top `.tabs` look in `index.html`, so it reads as part of the CW-266 page:

- `.switch`: `display:inline-flex; gap:2px; padding:2px; background:var(--soft); border-radius:8px`.
- `.seg`: no border, `height:1.75rem` (2.25rem under 30rem for touch), `padding:0 var(--s3)`, `color:var(--muted)`, `font-size:var(--t-small)`, weight 500. Hover: `color:var(--fg)`.
- `.seg[aria-expanded="true"]`: `background:var(--card); color:var(--fg); font-weight:600; box-shadow:0 1px 2px var(--shadow)` (the selected tab look).
- `.seg:disabled`: `opacity:.5`, as other disabled buttons.
- No chevron. The `summary::after` chevron stays for group sections only.
- `.panel`: `margin-top:var(--s2); padding-top:var(--s3); border-top:1px solid var(--line)`. On an `attn` or blocked card the border uses the card's own tint, unchanged.
- Removed: `.foot .summary, .foot .meta { margin-right:auto }`, `.foot > details`, `.foot > details > summary:hover`, `.foot > details[open]` and its summary rule.

### 4. Behaviour

- Click (or Enter/Space) on a closed segment: it opens, the other closes. On the open segment: it closes. Done in the click handler by flipping `aria-expanded` and `hidden` in place; nothing is rebuilt. Then `draw()` runs, so a Details body (and a merged row's lazily filled one) fills, as the `toggle` listener does today.
- Escape with focus on an open segment or inside its panel: the panel closes and focus goes to its segment.
- Opening does not move focus. Tab order: segment, segment, then the panel's links.
- The `toggle` listener keeps only the `details.group` branch (collapsed sections) and loses the `details.info` branch.

### 5. Keyboard and screen reader

- Each segment is a native `<button>` with `aria-expanded` and `aria-controls` (the disclosure pattern). A screen reader reads "Agents 3, collapsed, button" and "Details, expanded, button".
- The two sit in `role="group"` labelled `<id> panels`, so a reader hears which ticket they belong to when tabbing down a list.
- Each panel is `role="region"` labelled by its segment ("Agents region").
- A disabled segment is skipped by Tab and read as dimmed in browse mode, with its `title` as the reason.
- Focus ring: the existing `button:focus-visible` rule.
- Not arrow-key tabs: these are two toggles, both can be off, and Tab between two buttons is enough.
- The counter (below) is not `aria-live`: a minute tick read aloud on every card would be noise.

### 6. Open state across a poll

Same mechanism, new selectors. Before a rebuild the page reads which panel is open per row and passes the same two sets the renderers take today, so `renderStatus(groups, open, collapsed, info)`, `renderMerged(list, page, size, open, info)` and `renderChief(api, page, open)` keep their signatures:

| Today | After |
|---|---|
| `details.chart[data-ticket][open]` | `.seg[data-ticket][data-view="agents"][aria-expanded="true"]` |
| `details.info[data-ticket][open]` | `.seg[data-ticket][data-view="details"][aria-expanded="true"]` |
| `details.chart[data-merged][open]`, `details.info[data-merged][open]` | the same with `data-merged` |
| `details.chart[data-pm][open]` | `.seg[data-pm][data-view="agents"][aria-expanded="true"]` |

- The renderer opens Agents when the id is in `open`, else Details when it is in `info`. Clicks keep the sets disjoint; if both hold an id, Agents wins.
- An Agents view whose ticket lost its tasks comes back closed (the segment is disabled).
- `drawMerged` and `drawCos` still compare html rendered with every panel closed, so opening one is not a change and does not redraw.
- A selection inside an open Details body survives the tick as today: the body's html is compared before it is written.

### 7. Waiting counter

Applies to cards whose stage starts with `awaiting-`: `awaiting-merge`, `awaiting-build`, `awaiting-review`. `blocked` keeps its `next` line, because there it is the question the user must answer.

- **Text.** `waitText(stageAt, now)`, exported from `app.js`, returns `waiting <elapsed>`:
  - under a minute: `waiting <1m`
  - under an hour: `waiting 42m`
  - under a day: `waiting 3h 16m` (`3h` when the minutes are 0)
  - a day or more: `waiting 3d 4h` (`3d` when the hours are 0), however long
  - always rounded down, so it never overstates. A `stageAt` in the future (clock skew) reads `waiting <1m`.
  - `''` when `stageAt` is missing or does not parse.
- **Markup.** In place of `<p class="next">`: `<p class="wait" data-ticket="CW-341"><time datetime="<stageAt>" title="Since 2026-11-14 05:24">waiting 3h 16m</time></p>`, muted, small, `font-variant-numeric:tabular-nums`. The full date is in the tooltip, since `HH:MM` alone is unclear after a day.
- **Status sentence.** For `awaiting-*`, `stageSentence` drops ` since HH:MM` (the counter says it better). Other stages keep it. Flat Up next rows keep `Waiting to build since 12:04`: no `awaiting-*` stage lands in a flat band.
- **Ticking.** `draw()` already runs every second and refreshes `.summary[data-ticket]` in place. It gains the same loop for `.wait[data-ticket] time`: recompute `waitText`, write `textContent` only when it changed (once a minute). Nothing is rebuilt, so open panels, focus and selections stay. `stageAt` does not change while a ticket waits, so the poll's status compare does not trigger a rebuild either.
- **No `stageAt`.** The status sentence shows alone; no counter and no `next` line. The long line does not come back.
- **The full status line** stays one click away in Details, in its existing `Next` row. No change to `renderDetails`.
- **State text stays.** `.agent-team/state.json`'s `status` is what a fresh Chief of Staff thread reads to pick a ticket up, so it is not shortened. This is a display change only; `chief-of-staff/state-keys.md` and `approvals.md` keep how status lines are written. The display change is enough because the counter needs only `stageAt`, which `cos_state.py` already stamps.

### 8. GUY-346 before and after

Before (main today, at 08:40, `stageAt` 05:24):

```
┌──────────────────────────────────────────────────┐
│ Split fathom tickets into their own tracker   ⧉ │
│ GUY-346 · (High) · PR                            │
│ Spec is waiting for your approval since 05:24    │
│ awaiting-spec since 05:24: fathom-only spec at   │
│ 368b05e, keeps GUY prefix, placeholder issues…   │
│ [ Open spec ]                                    │
│ 2 agents · 18m 40s · $1.92  Agents 2 ⌄ Details ⌄ │
└──────────────────────────────────────────────────┘
```

After:

```
┌──────────────────────────────────────────────────┐
│ Split fathom tickets into their own tracker   ⧉ │
│ GUY-346 · (High) · PR                            │
│ Spec is waiting for your approval                │
│ waiting 3h 16m                                   │
│ [ Open spec ]                                    │
│ ⟦ Agents 2 │ Details ⟧  2 agents · 18m 40s · $1.92 │
└──────────────────────────────────────────────────┘
```

At 09:24 the next morning the same card reads `waiting 1d 4h`. Hovering it shows `Since 2026-11-14 05:24`. Details' `Next` row still holds `awaiting-spec since 05:24: fathom-only spec at 368b05e, keeps GUY prefix, placeholder issues keep numbers #289-348, 43 tickets renumbered, merge waits for ...` in full.

### 9. Mockups

`⟦ … ⟧` is the switch track. `▣Agents` marks the pressed segment, `░` a disabled one.

**Live card, closed**

```
┌──────────────────────────────────────────────────┐
│ Add Jira adapter retries                      ⧉ │
│ CW-341 · (Medium) · PR                           │
│ Building since 14:02                             │
│ checks green, waiting for the review agent       │
│ ⟦ Agents 3 │ Details ⟧  3 agents · 41m 05s · $2.10 │
└──────────────────────────────────────────────────┘
```

**Agents open**

```
┌──────────────────────────────────────────────────┐
│ Add Jira adapter retries                      ⧉ │
│ CW-341 · (Medium) · PR                           │
│ Building since 14:02                             │
│ checks green, waiting for the review agent       │
│ ⟦▣Agents 3 │ Details ⟧  3 agents · 41m 05s · $2.10 │
│ ──────────────────────────────────────────────── │
│ ┌ spec      ███████                 9m   $0.40 ┐ │
│ │ build            ██████████████  24m  $1.30  │ │
│ │ review                     ████   8m  $0.40  │ │
│ └ Total                            41m  $2.10 ┘ │
└──────────────────────────────────────────────────┘
```

**Details open** (Agents closes; the buttons stay put)

```
┌──────────────────────────────────────────────────┐
│ ...                                              │
│ ⟦ Agents 3 │▣Details ⟧  3 agents · 41m 05s · $2.10 │
│ ──────────────────────────────────────────────── │
│ Issue #341 · Spec · PR #352                      │
│ STAGE  build    RISK  Medium (touches the api)   │
│ NEXT   checks green, waiting for the review agent│
│ AGENTS 1 session, 3 tasks  TOKENS 410k  COST $2.10│
│ SPEC                                       Open │
│ ...                                              │
└──────────────────────────────────────────────────┘
```

**Done ticket with no Gantt tasks** (merged list)

```
Fix typo in install message
⟦░Agents 0 │ Details ⟧  CW-339 · merged today 13:10 · $0.12 · PR
───────────────────────────────────────────────────────────────
Fix the progress bar width
⟦ Agents 2 │ Details ⟧  CW-338 · merged today 11:55 · $1.40 · PR
```

Details is in the same column on both rows.

**Project-manager row** (Chief of Staff tab)

```
Backlog ranking                                  ⧉
⟦ Agents 1 ⟧  ● finished · updated today 09:12
```

**Phone width** (360px, one column, 16px gutter)

```
┌────────────────────────────────┐
│ Add Jira adapter retries     ⧉ │
│ CW-341 · (Medium) · PR         │
│ Building since 14:02           │
│ checks green, waiting for the  │
│ review agent                   │
│ ⟦▣Agents 3 │ Details ⟧         │
│ 3 agents · 41m 05s · $2.10     │
│ ────────────────────────────── │
│ spec                  9m $0.40 │
│ ███████                        │
│ build                24m $1.30 │
│       ██████████████           │
└────────────────────────────────┘
```

The foot wraps: the control keeps its own line and the summary drops under it. Segments are 2.25rem tall here. The Gantt already stacks its rows below 36rem (container query), unchanged.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `panelSwitch` replaces `chartToggle` and the pairs in `ticket()`, `renderMerged` and `teamList`; panels after `.foot`; `waitText` and the `awaiting-*` branch in `ticket()` and `stageSentence`; `draw()` refreshes `.wait`; click and Escape handling for `.seg`; new open-state selectors in `poll`, `drawMerged`, `drawCos`; `toggle` listener keeps only groups. |
| `agent-team/scripts/dashboard/page/index.html` | `.switch`, `.seg`, `.panel`, `.wait` rules; the `.foot > details*` and `margin-right:auto` rules go. |
| `agent-team/scripts/dashboard/page/app.test.js` | Tests below. |
| `agent-team/.claude/skills/chief-of-staff/state-keys.md` | One sentence in the `stageAt` bullet: the card shows `<stage> since HH:MM`, and a live `waiting …` counter for `awaiting-*` stages. Not a change to how status is written. |

`groups.ts` does not change: `Row` already carries `next` and `stageAt`, and the full `next` must still reach Details. `api.ts`, the server and the state scripts do not change.

### Tests that move

Rewritten for the new markup (same rules, new selectors):

- `a card with sessions gets a closed chart that reopens when its id is in the open set`
- `each ticket has a closed Details section …` (its `section()` helper reads the Details panel instead of `<details class="info">`)
- `a merged row has a closed Details section filled only when open …`
- `merged row with sessions has a closed Agents chart …; one without has none` becomes "… one without has a disabled Agents segment"
- `a running ticket helper is a placeholder card …` (the helper now has a disabled Details segment, so the "no Details" check becomes "no Details panel and no issue link")
- `the Chief of Staff tab renders …` (the `data-pm` open check)
- `the status sentence … ends with since HH:MM only when stageAt parses`: the `awaiting-build` case drops ` since 09:05`

New, one table each (`AGENTS.md` § Testing):

- `waitText`: missing, unparsable, future, 30s, 42m, 3h 0m, 3h 16m, 3d 0h, 3d 4h, 40d → the strings above.
- One rule over every row type (live card, flat row, blocked row, helper, merged with and without tasks, pm): the switch is the first child of `.foot`, has both segments (pm: Agents only) in the same order, opens exactly the view the sets name, at most one panel is not `hidden`, and a row with no tasks has a disabled Agents segment and no Agents panel.
- An `awaiting-*` card with `stageAt` shows the `.wait` counter and no `<p class="next">`; without `stageAt` it shows neither; a `build` card still shows `next`; Details' `Next` row holds the full text in all three.

No test for the CSS, the click handler or the Escape key (small UI interactions, per `AGENTS.md`); the PR's proof covers them with screenshots.

## Proof for the PR

Screenshots in light and dark: a card closed, with Agents open, with Details open; the merged list with a no-task row above a row with tasks; a pm row; phone width; GUY-346-style waiting card before and after. One short check that an open panel stays open across two polls and while the counter ticks over a minute.

## Non-goals

- What the Agents chart or the Details body shows.
- The dashboard server, the API, `groups.ts` data, or how the Chief of Staff writes status lines.
- The risk pill (CW-332).
- Widening a card when a panel opens (see Calls I made).

## Calls I made

- **Agents is drawn disabled (`Agents 0`) when there are no tasks**, rather than hidden. It costs a dimmed button on many merged rows, but Details never moves, which is problem 2.
- **The control goes first on the foot line, before the meta text**, on flat and merged rows too, so it is one fixed column down a list. On those rows the id now comes after the control.
- **Project-manager rows get Agents only**, no disabled Details, since they will never have a Details body.
- **Ticket helper cards get a disabled Details** to match ticket rows.
- **The pm row's meta line moves into the foot** beside the control, so pm rows match the others.
- **Disclosure buttons, not ARIA tabs**: both panels can be closed, which tabs cannot express.
- **No drawer or modal now.** The narrow panel inside a 22rem card stays as today; a wider view is a later ticket if wanted.
- **No card widening on open.** Spanning the open card across the grid would leave holes or shuffle the other cards.
- **Counter format**: `waiting <1m`, `42m`, `3h 16m`, `3d 4h`, rounded down, two units at most, no weeks.
- **Counter only on `awaiting-*`**; `blocked` keeps its `next` line because that is the question for the user.
- **`awaiting-*` sentences drop ` since HH:MM`**; the full date moves to the counter's tooltip.
- **No `stageAt`: no counter and no `next` line**, rather than falling back to the long text.
- **The counter is not announced** by screen readers (no `aria-live`).
- **Escape closes an open panel** and returns focus to its segment.
- **Segments are 2.25rem tall under 30rem** for touch; 1.75rem elsewhere, matching the other buttons.
- **`state-keys.md` gets a one-sentence doc update** so it does not describe the old card; how status is written does not change.
