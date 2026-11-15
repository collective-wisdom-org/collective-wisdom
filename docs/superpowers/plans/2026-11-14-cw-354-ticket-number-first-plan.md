# CW-354 plan: ticket number first, Spec and PR links on every row

**Spec:** [2026-11-14-cw-354-ticket-number-first-design.md](../specs/2026-11-14-cw-354-ticket-number-first-design.md)

Files: `agent-team/scripts/dashboard/page/app.js`, `agent-team/scripts/dashboard/page/index.html` (CSS), `agent-team/scripts/dashboard/page/app.test.js`.

## Task 1: markup (app.js)

1. Add a shared `rowHead(id, idHtml, title, extra)` helper used by `ticket()` and `renderMerged()`: `<div class="head"><span class="id">…</span><span class="title">…</span>{extra}</div>`. The id is `link(issueUrl, id)` (plain text without an http(s) url); a ticket helper keeps `Ticket helper`, unlinked. A row with no title shows the id alone (no title span).
2. Remove the `<span class="id">` part from the `meta` parts in `ticket()` and `renderMerged()`.
3. Add `specSpan(url)` beside `prSpan(url)` (same http(s) rule, label `Spec`, class `spec`). Meta order: risk, Spec, PR, stage phrase (live rows); merge time, cost, tokens, Spec, PR (merged rows). Helper rows show neither.
4. `renderDetails()`: drop the Issue, Spec and PR links; the links line keeps only the thread link and is omitted without one. Remove the now-unused `num`/`numbered` helpers.

## Task 2: CSS (index.html)

`.head .id { flex:none; color:var(--muted); font-variant-numeric:tabular-nums; }`, id link muted with `--fg` on hover (as `.meta a`), no wrap. Check the meta rules still read with the id gone from `.meta`. Phone width: no horizontal scroll.

## Task 3: tests (app.test.js)

One table-driven test over `renderStatus` and `renderMerged`: live card, flat row, blocked row, merged row, each with http, missing and `javascript:` spec and PR urls. Assert: `.head` has `class="id"` before `class="title"`; `Spec` and `PR` links appear in the meta line exactly when the url is http(s); no `href` holds a non-http url; the Details links line has no Issue, Spec or PR link. Update existing assertions that pin the old order (meta starting with the id, the Details `Issue #N · … PR #N` line, `Open spec` stays).

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
