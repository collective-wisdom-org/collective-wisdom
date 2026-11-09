# Dashboard Friendly Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the dashboard page so each ticket reads as one headline, one plain status sentence and at most one action, with plain-word section names and a calmer look.

**Architecture:** Page-only change in `agent-team/scripts/dashboard/page/`. New pure, exported helpers in `app.js` (labels, status sentences, risk text, day words, action link, Gantt summary) feed the existing render functions, whose markup changes; the browser shell keeps its selectors. `index.html` gets a new token set and component styles.

**Tech Stack:** Vanilla ES module, inline CSS with `light-dark()`, `node --test` (Node 24+). No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-08-dashboard-friendly-redesign-design.md`

**Local only:** the user wants this built and tried on their own project before any PR. Work on branch `feat/dashboard-friendly-redesign` in the worktree from Task 0; commit there; do not push and do not open a PR.

## Global Constraints

- Dependencies identical: one `index.html` with inline CSS, one `app.js` ES module, tests in `app.test.js`. No framework, build step, web font, icon font or image. CSP stays `default-src 'self'; style-src 'self' 'unsafe-inline'`.
- No change to `api.ts`, `merged.ts`, `server.ts`, `groups.ts`, the state scripts, the status-pane mod or the agent-gantt mod.
- `data-group` keeps the API group name (for example `Awaiting merge approval`); only the shown label changes.
- Shell selectors keep their names: `details.chart`, `details.info`, `details.group[data-group]`, `.chart-body[data-ticket|data-merged|data-pm|data-chief]`, `.info-body[data-ticket|data-merged]`, `button[data-copy]`, `button[data-page]`, `button[data-pm-page]`, `button[data-tab]`, `#status`, `#merged`, `#cos`, `#cta`, `#error`.
- Every string still goes through `esc()`; only http(s) urls become anchors.
- Four type sizes: 22px title, 15px body, 13px small, 11px band label; system-ui; line height 1.5; spacing on a 4px scale.
- Tokens (light / dark): page `#fafafa` / `#000000`; card `#ffffff` / `#111111`; line `#e5e7eb` / `#ffffff14`; text `#111827` / `#f5f5f5`; muted `#6b7280` / `#a1a1a1`; accent `#2563eb` / `#60a5fa`; attention `#b45309` / `#f59e0b`, tint `#fffbeb` / `#2a1f0a`; red `#b91c1c` / `#f87171`, tint `#fef2f2` / `#2a1212`; green `#15803d` / `#4ade80`. Dark page and card values do not move. Any pair under 4.5:1 is nudged and the ratio reported.
- Prose follows the `human-writing` skill: plain sentences, no em dashes.
- Tests: table-driven, one per rule, not one per edge case; test lines stay under feature lines.
- Commits: conventional (`feat:`), with the attribution trailer the session gives.

## Review Focus

Failure modes the spec implies; each has a test in the task that owns it.

1. A ticket with an empty title shows its id as the headline, and no empty headline element. (Task 3)
2. A risk of `not rated yet` or empty shows as `not rated yet`, never `not rated yet risk`. (Task 1)
3. An unknown stage or unknown group name containing markup renders escaped. (Task 1)
4. A missing, empty or non-http(s) url draws no action link and does not throw. (Task 1, Task 3)
5. A merged entry with no `spend`, no `gantt` or a bad `mergedAt` still renders a row; missing parts are skipped. (Task 3)

---

### Task 0: Worktree and spec

**Files:**
- Create: `.worktrees/dashboard-redesign/` (worktree on branch `feat/dashboard-friendly-redesign`)

- [ ] **Step 1:** Confirm `.worktrees` is ignored (`git check-ignore .worktrees`); the root checkout is not touched after this task.
- [ ] **Step 2:** `git worktree add .worktrees/dashboard-redesign -b feat/dashboard-friendly-redesign main`. Expected: clean worktree on the new branch.
- [ ] **Step 3:** Copy the untracked spec and this plan from the root checkout's `docs/superpowers/` into the same paths in the worktree, commit them (`docs: add dashboard redesign spec and plan`), then delete the two untracked originals from the root checkout so the root stays clean.
- [ ] **Step 4:** Run the baseline in the worktree: `node --test agent-team/scripts/dashboard/page/app.test.js`. Expected: PASS before any change. All later paths are relative to the worktree.

### Task 1: Pure helpers in `app.js`

**Files:**
- Modify: `agent-team/scripts/dashboard/page/app.js` (near `STAGE_WORDS` and `riskClass`)
- Test: `agent-team/scripts/dashboard/page/app.test.js`

**Interfaces:**
- Produces (all exported):
  - `groupLabel(name: string): string`
  - `stageSentence(stage: string): string`
  - `riskText(risk: string): string`
  - `dayWords(ms: number, now: number): string`
  - `actionFor(row: {stage?: string, prUrl?: string, specUrl?: string, issueUrl?: string}): {label: string, url: string} | null`

- [ ] **Step 1: Write failing tests**, one table-driven test per helper, in `app.test.js`:
  - `group labels`: the nine pairs from spec section 1 map as listed (for example `Awaiting merge approval` to `Ready to merge`, `Other` to `Blocked or waiting`); `groupLabel('<b>x</b>')` returns the input unchanged (callers escape).
  - `stage sentences`: the ten stages from the spec table give the exact sentences; `stageSentence('some-new-stage')` equals `some new stage`.
  - `risk text`: `Low (small change)` to `low risk`, `Medium` to `medium risk`, `HIGH` to `high risk`, `not rated yet` and `''` to `not rated yet`, `unclear` to `not rated yet`.
  - `day words`: with `now` at 2026-11-08 15:00 local, a time earlier that day gives `today`, 2026-11-07 gives `yesterday`, 2026-11-05 gives `2026-11-05`, `NaN` gives `''`.
  - `action link`: `awaiting-merge` with `prUrl` gives `{label: 'Open PR', url}`; `awaiting-build` with `specUrl` gives `Open spec`; `blocked` with `issueUrl` gives `Open issue`; each is `null` with the url missing, `''` or `javascript:alert(1)`; stage `build` is `null`.
- [ ] **Step 2: Run** `node --test agent-team/scripts/dashboard/page/app.test.js`. Expected: the new tests FAIL (not exported).
- [ ] **Step 3: Implement the five helpers.** `GROUP_LABELS` and `STAGE_SENTENCES` are module-level `Map`s holding the spec's tables verbatim; `riskText` reuses the first-word match from `riskClass`; `dayWords` compares local calendar dates; `actionFor` reuses `isHttp`. Export `stageWords` unchanged in behavior.
- [ ] **Step 4: Run the file again.** Expected: new tests PASS, older tests unchanged so far.
- [ ] **Step 5: Commit** `feat: add label, sentence and action helpers to the dashboard page`.

### Task 2: Bands, group labels and the header sentence

**Files:**
- Modify: `app.js` (`BANDS`, `renderStatus`, `renderBadges`)
- Test: `app.test.js` (update the tests at the `header badges...`, `status sections draw open...` and `groups sort into bands...` cases)

**Interfaces:**
- Consumes: `groupLabel` from Task 1.
- Produces: `renderBadges(groups): string` keeps its name and signature and returns `<span class="hs">…</span>` markup, never empty for an array input.

- [ ] **Step 1: Update/write failing tests.**
  - Bands: `renderStatus` headings read `Your turn`, `In progress`, `Up next` in that order; each group `<summary>` shows `groupLabel(name)` escaped while `data-group` still holds the API name; band order, api order inside a band and empty-band-not-drawn assertions stay.
  - Header, table-driven over group lists: need=2/progress=3/waiting=1 gives text `2 need you · 3 in progress · 1 waiting`; need=1 gives `1 needs you`; need=0 and others zero gives `Nothing needs you`; need=0 with progress=3 gives `Nothing needs you · 3 in progress`; one blocked ticket in `Other` gives a trailing `1 blocked` in a `.hs-blocked` span and is not counted in `waiting`; zero counts other than the lead are left out; the need part sits in `.hs-need` only when above zero.
- [ ] **Step 2: Run** the file. Expected: FAIL.
- [ ] **Step 3: Implement.** Rename band names in `BANDS` (slugs stay `needs`, `progress`, `queued`). Change the `<h2>Merged</h2>` heading in `index.html` to `Done` in Task 5, not here. `renderBadges` counts by band as in the spec's header-counts call; blocked rows are those with stage `blocked` in group `Other`.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: plain-word bands and one-sentence header on the dashboard`.

### Task 3: Ticket cards, rows, Details and the Done list

**Files:**
- Modify: `app.js` (`ticket`, `renderDetails`, `renderMerged`, `spent`, new `ganttSummary`)
- Test: `app.test.js` (update the cases for the copy button, Details, Spec/PR order, merged rows, merged spend)

**Interfaces:**
- Consumes: `riskText`, `stageSentence`, `actionFor`, `dayWords` (Task 1).
- Produces: `ganttSummary(sessions, now): {agents: number, ms: number, cost: number | null} | null`, `null` for no sessions. `renderGantt` is refactored to call the shared active-time computation so the math exists once; its output does not change.

- [ ] **Step 1: Write/update failing tests.**
  - Card (a ticket in `Building` with title, risk `Low`, next `x`, gantt of one task): contains, in this order, the title, a meta line with the id link and `low risk`, the sentence `Building`, the next text, then the footer summary and the `Agents` and `Details` `<details>` elements with their `data-ticket` hooks and pill count. No `badge risk` element and no stage badge.
  - Empty title: headline is the id link text and there is exactly one element with class `title`.
  - Action, table-driven over rendered cards: `awaiting-merge` card has one `a.action` with text `Open PR` and the escaped href; `build` card has none; an `awaiting-build` card with `specUrl: 'ftp://x'` has none.
  - Blocked in `Other` renders as a flat row with class `blocked`, the sentence `Blocked. Needs an answer from you` and `Open issue`.
  - Copy button: no `data-copy` button outside `.info-body`; the Details body for a row with `threadLink` contains `button[data-copy]` with the exact link and text `Copy thread link`. Spec and Issue links still appear in Details; the card face has a quiet `PR` text link when `prUrl` is http(s).
  - `ganttSummary`: one session with two tasks and a subagent returns the agent count, the union of active time in ms and the summed cost; any unpriced row gives `cost: null`; footer text for it reads `3 agents · 41m 05s · $2.10`, with the cost part skipped when null and the whole footer summary absent without a gantt.
  - Done rows: meta line reads `CW-248 · merged today 14:02 · $2.10 · 1.2M tokens`; an entry with no `spend`, no `gantt` and `mergedAt: NaN` still renders its title and id and omits the missing parts without throwing.
  - Hostile: a title, `next` and unknown stage containing `<img onerror>` come out escaped.
- [ ] **Step 2: Run** the file. Expected: FAIL.
- [ ] **Step 3: Implement.** Card markup order is spec section 2; Your turn cards (groups in the `needs` band) carry class `attn`, blocked rows class `blocked`. Footer holds the summary text and the two existing `<details>` summaries unchanged in hooks. The action is `<a class="action" href target=_blank rel="noopener noreferrer">` placed per the builder-choice rule: it must not overflow at 300px. `renderDetails` swaps the `<code>threadLink</code>` item for the copy button. Merged rows: the header row keeps id/title first, then the muted meta line from `dayWords`, `clock`, `dollars`, `tokens`.
- [ ] **Step 4: Run.** Expected: PASS, and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.
- [ ] **Step 5: Commit** `feat: one-headline ticket cards and calmer Done rows`.

### Task 4: Chief of Staff tab

**Files:**
- Modify: `app.js` (`stateBadge`, `threadButton`, `renderChief`)
- Test: `app.test.js` (the Chief of Staff case)

**Interfaces:**
- Consumes: `dayWords` (Task 1).

- [ ] **Step 1: Update failing test.** State renders as `<span class="state state-running">running</span>` with no `badge` class; the thread control is a `button[data-copy]` with text `Copy thread link`; a PM row title is `Backlog ranking` or `Hygiene` (unknown role as escaped text) with meta `updated today 14:02` when the first session has `updatedAt`; pager buttons and `data-pm-page` hooks unchanged; empty strings unchanged.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** The dot is CSS only (`::before`), not a character.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: apply the new card and row style to the Chief of Staff tab`.

### Task 5: Styles, tabs and contrast (`index.html`)

**Files:**
- Modify: `agent-team/scripts/dashboard/page/index.html`
- Create (outside the repo): `<scratchpad>/contrast.py`, a one-off ratio check

No test file; this is visual and checked in Task 6.

- [ ] **Step 1: Replace the `:root` tokens** with the Global Constraints set (names kept short and semantic: `--bg --card --line --fg --muted --accent --attn --attn-tint --red --red-tint --green`), remove tokens nothing uses, and keep the `data-theme` overrides.
- [ ] **Step 2: Restyle** for every class the new markup uses, per spec sections 2 to 6: cards (no border, 12px radius, 16px padding, 12px gap), `.ticket.attn` (3px attention left edge, tint), `.row.blocked` (red edge), `.meta`, `.status`, `.agent-text` (two-line clamp), `.foot`, `.action` (filled accent link), quiet text-button chevron toggles for `details.chart > summary` and `details.info > summary` (chevron drawn with a CSS border, rotating on `[open]`), `.hs`, `.hs-need`, `.hs-blocked`, band label (11px small caps, muted, letter-spaced, no hairline), group summary, segmented tabs (track in card colour, selected segment filled), error banner, `.state` dot, Gantt track/bars (6px radius; running bars attention, done bars green, stale faded). Change `<h2>Merged</h2>` to `<h2>Done</h2>`.
- [ ] **Step 3: Contrast script.** Compute WCAG ratios in Python for text on page and card, muted on page and card, accent on card, attention and red text on their tints, white on accent, in light and dark. Run it. Expected: every pair 4.5 or higher; nudge any value that fails and record the final ratios for the summary.
- [ ] **Step 4: Run the dashboard tests** from Task 3 step 4. Expected: PASS.
- [ ] **Step 5: Commit** `feat: new dashboard visual system with plain-word hierarchy`.

### Task 6: Run it locally against the user's project

**Files:** none changed (fixes found here go back to the owning task's files, with a commit each).

- [ ] **Step 1: Pick the data root.** Ask which project folder is the "nohands" one if it is not already known (candidates on this machine: `~/ibd_online`, `~/spotify-visualizer`). Never stop, restart or call `start.ts` for that project's own running dashboard. Read the main block of `server.ts` first; if it writes under the root, serve from a scratch copy of the project's `.agent-team` directory instead of the real one.
- [ ] **Step 2: Start the worktree's server** on a spare port: `node agent-team/scripts/dashboard/server.ts --root <root> --port 47999` from the worktree, in the background. Expected: `curl -s http://127.0.0.1:47999/health` returns `ok`.
- [ ] **Step 3: Look at it.** Capture 360px and 1280px, light and dark, with headless Chrome into the scratchpad, and view them. Check: Your turn first and amber, blocked red, sentences read naturally, nothing overflows at 360px, open Agents and Details survive a 5 second poll, Copy thread link works in Details, tabs and pager work.
- [ ] **Step 4: Fix** anything wrong in the owning file; rerun the dashboard tests; commit.
- [ ] **Step 5: Stop the server you started** and tell the user the URL to open (`http://127.0.0.1:47999`) and how to rerun it.
