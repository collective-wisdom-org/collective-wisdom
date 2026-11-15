# CW-402 plan: one card layout and an approve button

Spec: `docs/superpowers/specs/2026-11-15-cw-402-card-layout-approve-prefill-design.md` (approved). Files: `agent-team/scripts/dashboard/page/app.js`, `page/index.html`, `page/app.test.js`.

Test command (from the repo root): `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Task 1: card template

1. In `ticket()`, draw one template for every card (compact or not): `rowHead()` top row; `<div class="actions">` middle row only when the action link or approve controls exist; `.foot` bottom row = `panelSwitch()` control + one `.meta` holding risk, `Spec`, `PR`, `<span class="summary" data-ticket>` (time and cost, from `summaryLine()`), then the `Other` group stage phrase last. Parts missing leave no gap.
2. Remove the `status`, `wait` and `next` lines and the `.wait` live-refresh in the tick loop. Remove `waitText()` and `stageSentence`-only code paths that nothing else uses (keep `stageSentence` for the `Other` phrase). Remove the `blocked` entry from `ACTIONS`. Keep the `compact`, `attn`, `blocked` classes.
3. CSS: `.actions` flex row with a gap, `a.approve`/`button.approve` styles next to `a.action`; drop the rules only the removed lines used (`.status`, `.next`, `.wait`, `li.blocked .status`).
4. Update the existing tests that assert the old order, status/wait/next lines or `Open issue`; add one table-driven layout test (Your turn, in progress, Up next, Not started, blocked, helper rows).

## Task 2: thread glyph

`copyButton(link, { thread })` adds a speech-bubble svg before `COPY_ICON` inside the same button when `thread` is true. Ticket cards pass it; PM rows and the Chief of Staff card do not. Label and title stay `Copy thread link`. CSS: widen `button.copy-icon` only when it has the glyph.

## Task 3: approve and changes

1. Export `approveCommand(r, kind = 'approve')`: `approve N` or `changes N: ` for stages `awaiting-merge` and `awaiting-build`, N the digits after the last `-` of `r.id`; null otherwise.
2. Export `promptLink(chiefLink, text)`: from `<t3-thread://v2/ENV/THREAD>` build `t3code://threads/ENV/THREAD?prompt=<encodeURIComponent(text)>`; null when the link is missing or does not match (both ids `[A-Za-z0-9:._%-]+`, no other path part; reuse the id rule `api.ts` `cleanThreadId` uses).
3. `renderStatus(groups, open, collapsed, info, backlogPage, chiefLink)` gets the chief link, passed to `ticket()`; the shell passes `last.chief?.threadLink`. In the middle row: with a prompt link, `<a class="approve" href="t3code://...">Approve</a>` and `<a class="approve" ...>Changes</a>`; without, `<button type="button" class="approve" data-copy="approve N">` (and the changes one). Nothing posts to T3.
4. Tests: one table for `approveCommand` and the rendered controls per stage (both link and no-link), one for `promptLink` good and bad links.

## Task 4: check

Run the test command. Then, by hand, open `t3code://threads/<env>/<this thread>?prompt=approve%20402` with `open` on macOS and note in the PR whether T3 shows the draft unsent and the T3 version (`0.1.10-nightly.20261114.4695`). Do not send anything.
