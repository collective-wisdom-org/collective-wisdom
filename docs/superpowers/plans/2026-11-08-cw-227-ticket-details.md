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

## Change request (after PR #231 opened): per-stage detail

Spec: § Per-stage detail and § Calls I made for the change request. Read them first.

### Task 4: `agent-team/scripts/dashboard/details.ts` (new)

Follow the shape of `updated.ts` and `merged.ts` (`Run` type, `REFRESH_MS = 60_000`, `idle()`, a failed read keeps the last good value).

- Exports `type Detail` (spec § Per-stage detail).
- `specDetail(markdown)`: returns `Detail['sections']` for the headings `Goal`, `Builds`, `Leaves out`, `Non-goals`, `Out of scope`, `Calls I made`, `Touches` (match `## <name>` case-insensitively, section ends at the next `## `), in the spec's order, text trimmed and capped at 2000 characters with `…` after a cut. A heading with no text is skipped.
- `prDetail(json)`: parses `gh pr view --json body,files,comments`; returns `{ sections, files, moreFiles, reviews }` or `null` on bad JSON. Sections: `Summary` (else `Changes`), `Release note` (both `## ` sections of the body, same cap), and `Not proven` (the line starting `Not proven` in the body and the `- ` lines after it, up to the first blank line that is followed by a non-list line, or the end). Files: `{ path, add, del }` from `files[].path/additions/deletions`, first 30, `moreFiles` is the rest. Reviews: the last comment whose body starts `## Code review` and the last starting `## Security review`; verdict is the word after `Verdict:` (strip `*` and whitespace; `CHANGES NEEDED` stays two words), `url` from the comment when it is a `https://` string. Ignore entries of the wrong type.
- `createDetails({ run, git, now })` with `want(wants, cfg)` and `get(): Record<string, Detail>` and `idle()`. A want is `{ id, stage, specPath, specSha, pr }` from state. `awaiting-build` with `specSha` matching `/^[0-9a-f]{40}$/` and `specPath` matching `/^docs\/[\w./-]+\.md$/` with no `..`: call `git(['show', `${sha}:${path}`])` once per sha (cache by sha, a failed read retried after 60 s). `awaiting-merge` with an integer `pr`: `run(['pr', 'view', String(pr), '--repo', cfg.slug, '--json', 'body,files,comments'])`, at most once a minute per PR, last good result kept. Drop entries for tickets no longer wanted. `get()` has an entry only when there is at least one section.
- `gitRunner(root)`: `execFile('git', ['-C', root, ...args], { timeout: 5000, maxBuffer: 1 << 20 })`, no shell.

### Task 5: `api.ts`, `server.ts`

- `StatusRow` gets `detail?: Detail`. `buildApi` takes `details?: Record<string, Detail>` (default `{}`) and sets `row.detail` for ids in it. For `kind: 'spec'` it sets `url` to `${repo.url}/blob/${branch}/${specPath}` when `repo`, a string `branch` and a valid `specPath` are known; for `'changes'` it sets `url` to the `prUrl`.
- `server.ts`: create `createDetails({ run: ghRunner(root), git: gitRunner(root) })`; in `api()` call `details.want(...)` for every state ticket in a wanted stage with the cfg slug (`mergedCfg`, set for any GitHub repo), pass `details: details.get()` to `buildApi`.

### Task 6: `app.js`, `index.html`

- `renderDetails(r, now)` appends, after the `<dl>`, when `r.detail` has sections: a heading `Spec` or `Changes` (with `link(url, …)` for the open link, only when `isHttp`), then each section as `<h4>name</h4><p class="detail-text">text</p>`, the reviews as `Code review: PASS` lines (anchor when `isHttp(url)`), and the files as `<ul class="detail-files">` of `path +add −del` plus `and N more files`. Everything through `esc`. A ticket with a `detail` but no facts no longer shows the "Nothing more known yet" line.
- `index.html`: `.detail-text { white-space:pre-wrap; margin:0; overflow-wrap:anywhere }`, small muted `h4`, tight list.

### Task 7: tests, README

Per spec § Tests. README "Local dashboard": one sentence that Details shows the spec for a ticket waiting on build approval and the changes for one waiting on merge approval.

### Verify

Same commands as above, plus `node --test agent-team/scripts/dashboard/details.test.ts`.
