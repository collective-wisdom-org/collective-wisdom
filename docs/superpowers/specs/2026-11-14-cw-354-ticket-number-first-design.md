# CW-354: Put the ticket number first and the spec and PR links on every dashboard row

**Status:** Draft
**Ticket:** [#354](https://github.com/collective-wisdom-org/collective-wisdom/issues/354)
**Builds on:** CW-345 (PR #351, merged), the Agents and Details control this keeps, and CW-346 (PR #352, merged), the section headers. Edits the same page as CW-349 (Backlog pagination) and CW-350 (Done tab); whichever builds second rebases on the other.

## Goal

Every ticket row on the dashboard starts with its ticket number, and the Spec and PR links sit on the row itself, so you can find a ticket and open its spec or PR without opening Details.

## Today

Facts from main at `81c114b`, all in `agent-team/scripts/dashboard/page/app.js`.

- `ticket()` draws `.head` (title and copy icon) first, then a meta line built by `metaLine()`. The meta line starts with `<span class="id">`, the id linked to the issue. On a card the id sits under the title; on a flat row (Up next, Not started) it is the first part of the footer meta, after the Agents and Details control.
- The meta line carries `prSpan(r.prUrl)`, a `PR` link. There is no Spec link on any row. `r.specUrl` shows only in `renderDetails` and in the `Open spec` action of an `awaiting-build` card.
- `renderMerged()` builds its own row: title in `.head`, then a footer meta of id, merge time, cost, tokens and `PR`. Merged entries carry `specUrl` when the dashboard found the PR's spec (`api.ts`, `withExtras`).
- `renderDetails()` starts with a links line, `<p class="info-links">`: `Issue #N`, `Spec`, `PR #N`, then the thread link as `<code>`. So with Details open the PR and issue links show twice.
- `link()` and `isHttp()` already drop any url that is not http(s); a missing url gives plain text or nothing.

## Design

### The id goes first

The id moves out of the meta line into `.head`, before the title:

```html
<div class="head"><span class="id"><a href="…/issues/354">CW-354</a></span><span class="title">Put the ticket number first…</span><button class="copy-icon">…</button></div>
```

- One shared helper builds the head for `ticket()` and `renderMerged()`, so every row has the same order: id, title, copy icon (merged rows have no copy icon today and still don't).
- The id keeps linking to the issue through `link(r.issueUrl, r.id)`; with no http(s) issue url it is plain text, as today.
- A running ticket helper keeps `Ticket helper` in the id slot, unlinked, as today.
- With no title the title falls back to the id today (`r.title || r.id`). With the id now in front, that would print the id twice, so a row with no title shows the id alone.
- Style: `.head .id` is `--muted`, tabular figures, `flex:none` so it never wraps mid-id, with the existing `--s1` head gap before the title. The id's link takes the same muted color as `.meta a` and turns `--fg` on hover. The title keeps its weight, so the eye still reads the title, and the id lines up down the left edge of each list.

### Spec and PR on the row

A new `specSpan(url)` beside `prSpan(url)`, both in the meta line, Spec first:

- `Spec` shows when `specUrl` is http(s), `PR` when `prUrl` is http(s). Either is left out otherwise, as `prSpan` does today.
- Live rows: the meta line becomes risk, Spec, PR, then the stage phrase on flat rows. The helper still shows neither.
- Merged rows: merge time, cost, tokens, Spec, PR.
- Slim rows (Not started) have no spec or PR in the data, so nothing changes there beyond the id moving to the front.
- The `Open spec` button on an `awaiting-build` card stays. It is the one action that card asks of you, and the meta link is a quiet second way in.

### Details stops repeating links

`renderDetails()` drops `Issue #N`, `Spec` and `PR #N` from the links line. The line keeps the thread link alone, and is left out when there is no thread link, as an empty links line is today. The facts grid and the spec or PR text are unchanged.

### Phone width

At 360px the id is about 55px at the title size, so a title wraps one word earlier than today. The meta line already wraps at `·` boundaries, and adding `Spec` adds one short word.

### Before and after

```
Before (card)                         After (card)
Fix the backlog pager  [copy]         CW-349  Fix the backlog pager  [copy]
CW-349 · Low · PR                     Low · Spec · PR
Waiting for your merge approval       Waiting for your merge approval

Before (flat row)                     After (flat row)
Fix the backlog pager                 CW-349  Fix the backlog pager
[Agents 3|Details] CW-349 · Low · PR  [Agents 3|Details] Low · Spec · PR · Building since 09:05
  · Building since 09:05
```

## Tests

In `agent-team/scripts/dashboard/page/app.test.js`, one table-driven test over `renderStatus` and `renderMerged` rows: a live card, a flat row, a blocked row and a merged row, each with http, missing and `javascript:` spec and PR urls. Each case checks:

- the row's `.head` starts with `<span class="id">` before `<span class="title">`,
- `Spec` and `PR` links appear in the meta line exactly when their url is http(s), and no `href` carries a non-http url,
- the Details links line has no Issue, Spec or PR link.

Existing assertions that pin the old order (the meta line starting with the id, the Details links line text) are updated to the new markup.

## Out of scope

- The Agents and Details control, the waiting counter and the section headers.
- Project manager rows on the Chief of Staff tab, which have no ticket number.
- What the API sends: `specUrl`, `prUrl` and `issueUrl` already exist on the rows.

## Calls I made

- A row with no title shows the id alone, instead of the id followed by the id again as its title fallback.
- The Details links line keeps only the thread link; with no thread link the line is left out.
- Spec comes before PR on the row, the order the ship loop makes them.
- The `Open spec` button on a card waiting for build approval stays, though the row now has a Spec link too.
- The id is muted and the title keeps its weight, so the title still reads first; the id is not bold or set as a badge.
- The row PR link stays the bare word `PR`; the `PR #N` form leaves the page with Details' links.
- Merged rows get the id in front but still no copy icon.
