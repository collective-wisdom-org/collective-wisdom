# CW-227: An expandable details section on each dashboard ticket

**Status:** Draft
**Ticket:** [#227](https://github.com/collective-wisdom-org/collective-wisdom/issues/227)
**Related:** CW-225 (gantt own spans, PR #228, merged).

## Goal

Each open ticket on the dashboard has a closed `Details` section. Opening it shows what the API already knows about the ticket, without leaving the page. It stays open across polls.

## Today

Facts from `main` at `ca70a4e`.

- `ticket()` in `agent-team/scripts/dashboard/page/app.js` draws a card (`li.ticket`) or, in the Queued band, a flat row (`li.row`): the id linked to the issue, the title, a risk badge, a `PR` link, a `Copy thread link` button, the `next` line, and, when the ticket has tasks, an `Agents` `<details class="chart" data-ticket>` whose body `draw()` fills with `renderGantt`.
- The stage badge shows only in the `Other` group.
- `poll()` rebuilds `#status` only when the status JSON changed. In that JSON each `gantt` is reduced to its session ids and its task count, so new token or cost numbers alone do not rebuild the cards. Before a rebuild it collects the open `details.chart[data-ticket]` ids and passes them to `renderStatus(groups, open, collapsed)`.
- `draw()` runs every second and rewrites each `.chart-body[data-ticket]` from the latest `/api` data.
- A `StatusRow` from `buildApi` (`agent-team/scripts/dashboard/api.ts`) has `id`, `title`, `risk`, `next`, `stage`, and when known `issueUrl`, `prUrl`, `threadLink` and `gantt` (sessions, each with `updatedAt`, `stale`, `total` and rows with `tokens` and `cost`).
- Each gantt row holds its own usage only: a task row is the main thread's usage inside that task, and each subagent row is that subagent's (`buildRows` in `mods/agent-gantt/hooks/rows.ts`). Summing the rows the chart draws gives the whole without double counting. The chart's Total cost is that sum, through `sumCost`, which is null when any row is unpriced.
- `threadLink` is a `t3-thread://` link, not http, so `link()` shows it as text.

## Design

### Markup

`ticket()` adds, after the `Agents` section, on every card and flat row:

```html
<details class="info" data-ticket="CW-1"><summary>Details</summary><div class="info-body" data-ticket="CW-1">…</div></details>
```

Closed unless its id is in the new open set. The body is `renderDetails(r, now)`, a new exported pure function that returns a `<dl>` of the lines below, in this order. A line whose value is missing is left out entirely; a ticket with none of them gets `<p class="quiet">Nothing more known yet</p>`.

| Line | Value | Shown when |
|---|---|---|
| Stage | `STAGE_WORDS.get(stage) ?? stage.replace(/-/g, ' ')`, the same words the `Other` badge uses | `stage` is non-empty |
| Risk | `risk` in full | `risk` is non-empty |
| Next | `next` in full | `next` is non-empty |
| Issue | the URL, through `link(issueUrl, issueUrl)` | `issueUrl` is http(s) |
| PR | the URL, through `link(prUrl, prUrl)` | `prUrl` is http(s) |
| Thread | the link as escaped text in `<code>` | `threadLink` is non-empty |
| Agents | `N sessions, M tasks, K subagents` (singular for one; a zero part is left out) | `gantt` has a session |
| Tokens | `tokens()` of the sum of `tokens` over the rows the chart draws | `gantt` has a session |
| Cost | `dollars()` of the same sum the chart's Total uses | that sum is a number |
| Last update | `stamp()` of the newest session `updatedAt`, plus ` (stale)` when that session is stale | `gantt` has a session |

- Tasks are `taskCount(gantt)`, the number on the `Agents` pill. Subagents are the drawn rows of kind `agent`, at any depth. The rows "the chart draws" are the ones `ganttTasks` keeps (an older snapshot's `session` row is dropped when its session has task rows), so the details and the chart agree.
- Every value goes through `esc`, and only `link()` makes anchors, so a non-http URL is never an `href`.
- The `Copy thread link` button on the card stays.

### Keeping it open, and current

- `renderStatus(groups, open, collapsed, info)` takes a fourth set, the open `Details` ids. Default empty, so existing callers are unchanged. `poll()` collects `details.info[data-ticket][open]` ids before a rebuild, the same way it does for `details.chart`.
- Because a poll does not rebuild the cards when only numbers change, `draw()` also refreshes each `.info-body[data-ticket]` from the latest row. It writes the body only when `renderDetails` returns something other than what it last wrote for that id, so an unchanged body keeps a text selection.

### Style

In `index.html`, `details.info` takes the `details.chart` summary style (muted, small, pointer). The `<dl>` is a two-column grid: muted labels, values that wrap (`overflow-wrap:anywhere`, so a long URL or thread link does not widen the card).

## Tests

One new case in `agent-team/scripts/dashboard/page/app.test.js`, table-driven over two tickets through `renderStatus`:

- every field set, with markup in `next` and a two-session gantt with a subagent and every row priced: each line is present with the expected text, values are escaped, the issue and PR are anchors;
- only an id: the `Details` section is there and closed, its body is the quiet line, and it has no `<dt>`, no `href` and no empty `<dd>`.

Plus one assertion that an id in the open set renders `<details class="info" … open>`. Opening and polling in the browser is not unit tested (the shell is not under test today); it is checked by hand in the PR's proof.

`node --test agent-team/scripts/dashboard/page/app.test.js` passes, and so does the full `node --test` line in `AGENTS.md` § Workflow, since the PR touches `agent-team/scripts/dashboard/`.

## Non-goals

- New API fields (branch, spec link, stage history).
- The merged list.
- Any change to the `Agents` gantt chart.

## Calls I made

- **"Agent count" is split into sessions, tasks and subagents.** The `Agents` pill already counts tasks, so a bare "N agents" would be ambiguous. One line shows all three, with zero parts left out.
- **Cost is the chart's Total (prices.json), not Claude Code's reported `total`.** The two can differ (the chart shows a note when they do); matching the chart avoids two different dollar figures on one card. When any row is unpriced the Cost line is left out rather than shown as `–`.
- **Details refresh every second through `draw()`**, not only on a status rebuild. Without that the token, cost and last-update lines would freeze until something else on the card changed.
- **The details body has its own refresh guard** (last written html per id), so a selection inside an open details is not lost each second.
- **Issue and PR show their full URL** as the link text, since the card already has the short `PR` link and the id link.
- **Thread link is shown as text in `<code>`**, since it is not http and `link()` will not make it an anchor. The existing copy button stays the way to copy it.
- **Last update shows a date and clock time** with `stamp()`, as the merged list does, plus `(stale)` when that session went stale.
- **Flat rows in the Queued band get the section too**, since the ticket says each card and row.
- **A ticket with nothing to show gets one quiet line** instead of an empty box, so opening it does not look broken.
