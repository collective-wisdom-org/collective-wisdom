# CW-227 plan: an expandable details section on each dashboard ticket

Spec: `docs/superpowers/specs/2026-11-08-cw-227-ticket-details-design.md`

## Task 1: app.js (`agent-team/scripts/dashboard/page/app.js`)

1. Move the `STAGE_WORDS.get(stage) ?? stage.replace(/-/g, ' ')` expression into a small `stageWords(stage)` helper and use it in the `Other` badge and in the details.
2. Add `export function renderDetails(r, now)`. It returns a `<dl class="info-list">` of `<dt>label</dt><dd>value</dd>` lines in the spec's order (Stage, Risk, Next, Issue, PR, Thread, Agents, Tokens, Cost, Last update), a line left out when its value is missing, or `<p class="quiet">Nothing more known yet</p>` when none shows.
   - Issue and PR: `link(url, url)` only when `isHttp`. Thread: `<code>${esc(threadLink)}</code>`.
   - Gantt lines use `ganttTasks(r.gantt, now)`: sessions = `r.gantt.length`, tasks = `items.length`, subagents = count of drawn rows (items and their kids) with `kind === 'agent'`. Tokens = sum of `tokens` over every drawn row, shown with `tokens()`. Cost = `sumCost` of the same per-item sums the chart's Total uses (refactor so the chart and the details share one helper), shown only when a number. Last update = `stamp()` of the session with the largest `updatedAt`, plus ` (stale)` when that session is stale.
   - Every value through `esc`; only `link()` makes anchors.
3. `ticket()` adds, after the `Agents` section, `<details class="info" data-ticket="ID"[ open]><summary>Details</summary><div class="info-body" data-ticket="ID">${renderDetails(r, Date.now())}</div></details>` on cards and flat rows. `renderStatus(groups, open, collapsed, info = new Set())` takes the open set for it and passes it down.
4. Browser shell: `poll()` collects `details.info[data-ticket][open]` ids before a rebuild and passes them as `info`. `draw()` also refreshes each `.info-body[data-ticket]` from the latest row, writing `innerHTML` only when `renderDetails(row, now)` differs from the last html written for that id (a `Map`).

## Task 2: index.html

`details.info` takes the `details.chart` rules (margin, summary muted/small/pointer/hover). `.info-list` is a two-column grid: muted labels, values with `overflow-wrap:anywhere; min-width:0`, no default margins.

## Task 3: app.test.js

One table-driven test through `renderStatus` over two tickets: (a) every field set, markup in `next`, a two-session gantt with a subagent, every row priced: each line has the expected text, values are escaped, issue and PR are anchors; (b) only an id: the `Details` section is closed, body is the quiet line, no `<dt>`, no `href`, no empty `<dd>`. Plus one assertion that an id in the `info` set renders `<details class="info" ... open>`. Skip tests for the browser shell.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
