# CW-240: Redesign the dashboard Details section, render its markdown, pick spec or PR details by stage

**Status:** Draft
**Ticket:** [#240](https://github.com/collective-wisdom-org/collective-wisdom/issues/240)
**Related:** CW-227 (Details section, PR #231). Supersedes CW-235 (its `specUrl` field and `Spec` link are folded in here).

## Goal

The `Details` section on each dashboard ticket reads at a glance: facts on top in a few short groups, then the spec or PR text rendered as formatted markdown instead of raw characters. Every ticket card, every flat row and every merged row shows a `Spec` link beside its `PR` link when it has one. The text shown follows where the ticket is: the spec while it waits for build approval and while it builds, the PR from merge ready on, merged tickets included.

## Today

Facts from `main` at `bd5602a`.

- `ticket()` in `agent-team/scripts/dashboard/page/app.js` renders `<details class="info" data-ticket>` with an `.info-body` that `renderDetails(r, now)` fills: one `<dl class="info-list">` of ten facts (Stage, Risk, Next, Issue, PR, Thread, Agents, Tokens, Cost, Last update), then `renderDetail(r.detail)`: an `<h4>` and `<p class="detail-text">` (`white-space:pre-wrap`) per section, review lines and `ul.detail-files`. Every string goes through `esc()`, so markdown shows as raw `##`, `**`, `- `, backticks and `[text](url)`.
- `details.ts`: `createDetails().want(wants, cfg)` picks a spec read (`git show <specSha>:<specPath>`) for `awaiting-build` only and a PR read (`gh pr view N --json body,files,comments`, at most once a minute) for `awaiting-merge` only. `server.ts` passes only tickets in those two stages.
- `api.ts` `buildApi`: a `StatusRow` has `prUrl` but no spec url. The only spec url is `detail.url`, built from `branch` and `specPath`, and only once the spec was read.
- `merged.ts`: a `MergedEntry` has `id`, `title`, `prUrl`, `issueUrl`, `mergedAt`, `spend`, `gantt`; no detail, no spec. The merged ticket has left `state.tickets`, so its `specPath` and `specSha` are gone. `renderMerged` draws ten rows a page; the page number lives only in the browser (`mergedPage` in the shell).
- `cos_handoff.py` checks `specPath` against `docs/superpowers/specs/[A-Za-z0-9._-]+\.md` and `specSha` against `[0-9a-f]{7,40}`. `validSpecPath` in `details.ts` is looser.
- `poll()` keeps open `details.info[data-ticket]` across a rebuild, and `draw()` rewrites an `.info-body` only when its html changed, so a selection survives.

## Design

### 1. Layout

The open `Details` body becomes three blocks, top to bottom. Every block is left out when it has nothing to show; a body with nothing at all keeps `<p class="quiet">Nothing more known yet</p>`.

```
┌ Details ──────────────────────────────────────────────────────────┐
│ Issue #240 · Spec · PR #241 · Thread [code]          ← links line │
│                                                                   │
│ STAGE         RISK      NEXT                                      │
│ build         Medium    Builds the plan, then opens the PR        │
│                                                                   │
│ AGENTS               TOKENS   COST    LAST UPDATE                 │
│ 2 sessions, 5 tasks  1.2M     $3.10   21:40                       │
│ ───────────────────────────────────────────────────────────────── │
│ SPEC                                                     Open ↗   │
│ ▍Goal                                                             │
│ ▍ Rendered paragraph text, max 72ch wide, line-height 1.5.        │
│ ▍Builds                                                           │
│ ▍ • first bullet with `code` and a link                           │
│ ▍ • second bullet                                                 │
│                                                                   │
│ (changes kind) Reviews: [Code review PASS] [Security review PASS] │
│ Files (12)                                                        │
│   agent-team/scripts/dashboard/details.ts        +40  −12         │
└───────────────────────────────────────────────────────────────────┘
```

- **Links line** (`p.info-links`): `Issue #N`, `Spec`, `PR #N`, each through `link()` and only when its url is http(s), joined by ` · `. The thread link stays as escaped text in `<code>`, last. This replaces the Issue, PR and Thread rows of today's list, which printed full urls.
- **Facts** (`div.info-facts`): two small grids of label over value, each label in muted small caps. Row one is the ticket: Stage, Risk, Next (Next takes the rest of the row). Row two is usage: Agents, Tokens, Cost, Last update, with the same values and rules CW-227 set. A grid with no values is left out. On a narrow card the grid wraps.
- **Text** (`section.detail`): a header with `Spec` or `Changes` and the `Open` link at the right, then one block per section: the section name as a small bold label, and the rendered markdown under it in a box with a thin left border (`.detail-section`), readable line height, capped at about 72 characters wide. A section taller than about 20 lines scrolls inside its box (`max-height` and `overflow:auto`), so one long section does not push the rest off screen.
- **Reviews**: one row of badges, `Code review PASS` and `Security review PASS`, green for PASS and red for anything else, each linked to its comment when the url is http(s).
- **Files**: a heading `Files (N)` and a two-column grid: the path in monospace on the left, `+add −del` right-aligned. `and K more files` stays as the last line.

The styles go in `index.html` and reuse its existing tokens (`--s*`, `--t-small`, `--muted`, `--line`, `--b-low*`, `--b-high*`). `.detail-text`, `.info-list` and `.detail-review` go.

### 2. Markdown render

A new exported pure function `renderMarkdown(text)` in `app.js`, about 80 lines, with no dependency. The page already has every part it needs (`esc`, `isHttp`, `link`), and a library would be the page's first runtime dependency and would need a sanitizer on top.

It never emits input as markup. It splits the text into blocks line by line, and every piece of text that reaches the output goes through `esc()` before any tag is built around it.

Blocks:

| Input | Output |
|---|---|
| a line opening with ```` ``` ```` or `~~~`, up to the matching close (or the end) | `<pre><code>` of the escaped lines |
| `#` to `######` heading | `<p class="md-h">` with the inline render, bold. Real `<h*>` tags would fight the section labels |
| lines starting `- `, `* ` or `+ ` | `<ul><li>`; a marker indented by two or more spaces opens a nested list inside the last item, one level deep (deeper is treated as that level) |
| lines starting `1. ` (any number, `.` or `)`) | `<ol><li>` with the same nesting |
| a line indented under a list item | joined to that item's text |
| lines starting `> ` | `<blockquote>` with the inline render |
| a run of lines starting with `\|` | `<pre class="md-table">` of the escaped lines, so a table keeps its columns without a table parser |
| other non-blank lines | one `<p>` per run of lines, lines joined with a space |

Inline, on already-escaped text: a code span (`` `x` ``) is cut out first and becomes `<code>` with no further processing inside it; then `[label](url)` becomes `link(url, label)` only when the url is `http://` or `https://` (any other url leaves the label as plain text and drops the url); then `**x**` or `__x__` becomes `<strong>`, and `*x*` or `_x_` (not inside a word) becomes `<em>`. Bare urls stay text.

`link()` already sets `target="_blank" rel="noopener noreferrer"` and escapes the href. A `javascript:`, `data:` or `vbscript:` link, a raw `<script>` or `<img onerror>`, and markdown that tries to close an attribute all come out as escaped text. `renderDetail` calls `renderMarkdown(s.text)` for each section.

### 3. `specUrl` and the Spec link

- `api.ts` adds `specUrl?: string` to `StatusRow`: `<repo.url>/blob/<specSha>/<specPath>`, set only when there is a `repo`, `specPath` matches `^docs/superpowers/specs/[A-Za-z0-9._-]+\.md$` and `specSha` matches `^[0-9a-f]{7,40}$` (the `cos_handoff.py` rules). There is no stage filter: any open ticket with both values gets it.
- `detail.url` for a spec detail becomes `specUrl` (a commit url keeps working after the branch is deleted), so the `branch` check in `buildApi` goes.
- `MergedEntry` adds `specUrl?: string` and `detail?: Detail` (section 4).
- `ticket()` and `renderMerged` put `<span class="spec">${link(specUrl, 'Spec')}</span>` right before the `PR` span in `.sub`, only when `specUrl` is http(s). No span, no gap, when it is missing. The Details links line shows `Spec` the same way.

### 4. Which details show, by stage

`createDetails().want` and the `server.ts` filter change to:

| Stage | Detail |
|---|---|
| `awaiting-build`, `build`, `build-queued` | spec, from `specSha:specPath` (`validSha` loosens to 7 to 40 hex, matching `cos_handoff.py`; `git show` takes a short sha) |
| `awaiting-merge`, `merge`, `merge-queued` | PR, from `pr`, at most once a minute |
| merged | PR, by the entry's PR number, for the rows on the merged page the browser shows |
| any other | none |

The spec path check in `want` becomes the strict `cos_handoff.py` rule too, so only a path that could be a `specUrl` reaches git.

**Merged rows.** The browser sends the merged page it shows: `fetch('/api?mergedPage=N')`. The server parses `N` as an integer from 0 to 19 (200 merged PRs, 10 a page); anything else reads as 0. It wants a PR detail for those ten entries. `MergedEntry` gets a `number` it already parses (kept internal to the server; the API shape adds only `detail` and `specUrl`). A merged PR's read asks for `body,files,comments,mergeCommit` and goes through the same `prDetail` and the same one-minute pace and cache as an open PR, so turning pages back and forth does not read again inside the minute. Entries dropped from `want` are dropped from the cache, as today.

**Spec link on a merged row.** The spec is recovered from the PR itself: the merged PR's files list holds the spec it added. Of the PR's files, take those that match the strict spec path rule and whose name contains `-<prefix>-<n>-` for the row's ticket (lower case, for example `-cw-240-`). If exactly one matches, and `mergeCommit.oid` is a 40-character hex sha, `specUrl` is `<repo>/blob/<mergeCommit.oid>/<path>`. Otherwise there is no `Spec` link. This needs no new state and works for any merged PR the team shipped with a spec.

**Merged Details markup.** `renderMerged` adds, after the `Agents` section, `<details class="info" data-merged="<id>"><summary>Details</summary><div class="info-body" data-merged="<id>">…</div></details>`, filled by `renderDetails(e, now)`. Its facts are the links line and the usage row from the entry's `gantt`, then the PR text. It takes a second open set the same way `open` works for charts. `drawMerged` collects `details.info[data-merged][open]` before a rewrite, compares html with every section closed (as it does for charts), and `draw()` refreshes `.info-body[data-merged]` only when its html changed, so open state and a selection survive a poll there too.

### 5. Tests

Within the `AGENTS.md` § Testing budget, one table per rule:

- `page/app.test.js`
  - markdown elements: a table of input to expected markup (heading, bold, italic, inline code, fenced code, bullet list with a nested item, numbered list, link, paragraphs, table as `pre`).
  - hostile input comes out inert: `<script>`, `<img src=x onerror=…>`, `[x](javascript:alert(1))`, `[x](data:…)`, a link url with `"` in it, and backtick code holding `<b>`. Each row asserts no `<script`, no `onerror=` outside escaped text, and no `href` that is not http(s).
  - `Spec` link render: a row with `specUrl` has the `Spec` anchor right before the `PR` anchor in `.sub`, on a card, a flat row and a merged row; with no `specUrl` there is no `spec` span; a `javascript:` `specUrl` is no anchor.
  - the existing Details test updated to the new layout (links line, facts grids).
- `details.test.ts`: a table of stage to detail kind (`awaiting-build`, `build` and `build-queued` give spec; `awaiting-merge`, `merge`, `merge-queued` and a merged want give changes; `spec` and `blocked` give none), and a table for the merged spec recovery (one match, none, two, bad merge sha).
- `api.test.ts`: a `specUrl` case table (valid, short sha valid, missing sha, bad sha, bad path, `..` in path, no repo).
- `server.test.ts`: `mergedPage` parsing table (missing, `2`, `-1`, `abc`, `99`).

## Builds

- The new Details layout: links line, two fact grids, the text panel with rendered sections, review badges and the files grid.
- `renderMarkdown`, a small dependency-free markdown render that escapes first.
- `specUrl` on open ticket rows and merged rows, and a `Spec` link beside `PR` on every card, flat row, merged row and Details links line.
- Spec text for `build` and `build-queued` too; PR text for `merge`, `merge-queued` and merged rows.
- A `Details` section on each merged row, read for the visible merged page only.

## Leaves out

- Plan and as-built links.
- The `Agents` chart, merged paging and the spend columns.
- A new state key for merged tickets' spec paths.
- Markdown tables as real tables, images, raw HTML, strikethrough, task-list checkboxes, nesting deeper than one level, and reference-style links.

## Non-goals

- A general markdown engine. The render covers what specs and PR bodies here use and shows the rest as plain text.

## Calls I made

- **Merged details follow the browser's page through `/api?mergedPage=N`.** The ticket asks for reads only for the visible page; the server has no other way to know it. The parameter is clamped to 0 to 19 and changes only which PRs are read.
- **The spec link on a merged row is recovered from the PR's files and its merge commit.** The spec is one of the files the PR added, named with the ticket id, and the merge commit holds it at that path. If not exactly one file matches, the row shows no `Spec` link, as the ticket allows.
- **Tables render as a monospace `pre` block**, not an HTML table. It keeps columns readable with little code. Images, raw HTML and strikethrough show as plain text.
- **Headings inside a section render as bold paragraphs**, not `<h*>`, so they sit below the section label in the hierarchy.
- **A section taller than about 20 lines scrolls inside its own box.** No per-section expand toggle: a nested `<details>` would lose its open state whenever the body is rewritten.
- **Issue, PR and Thread move from full-url rows into one links line** (`Issue #N · Spec · PR #N`), which is shorter and puts `Spec` next to `PR` as asked.
- **`specSha` accepts 7 to 40 hex characters** for both `specUrl` and the spec read, matching `cos_handoff.py`; today's spec read wanted 40 only.
- **No markdown dependency.** About 80 lines in `app.js` instead of a library plus a sanitizer.

## Touches

None of these: data, money, auth, user email, migrations. It reads more from GitHub (`gh pr view` for up to ten merged PRs a minute while the merged list is shown) and renders untrusted PR and spec text as markup, so the security review should look hard at `renderMarkdown`.
