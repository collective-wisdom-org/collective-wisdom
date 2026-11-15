# CW-402: One layout for every dashboard card, and an approve button that prefills the command

**Status:** Draft
**Ticket:** [#402](https://github.com/collective-wisdom-org/collective-wisdom/issues/402)

## Goal

Every ticket card on the local dashboard is drawn the same way: a top row (number, title, thread copy button), an optional middle row (the one link that needs the user, plus an approve button), and a bottom row (Agents and Details, risk, `Spec`, `PR`, time, cost). A "Your turn" card gets an approve button that opens the Chief of Staff thread with `approve N` already typed in the input. The user still presses Send.

## Today

Facts from main at `6cab6af`, `agent-team/scripts/dashboard/`.

- `ticket()` in `page/app.js` draws two shapes. A compact card (flat, not blocked) is `rowHead()` then one `.foot` with the `panelSwitch()` control and the meta line. A full card (Your turn, in progress, blocked flat row) is the head, a `.meta` line, `<p class="status">`, `<p class="wait">` or `<p class="next">`, `a.action`, then a `.foot` with the control and `<span class="summary" data-ticket>` (time and cost).
- The tick loop refreshes `.summary[data-ticket]` every second from `summaryLine()` and the `waiting` counter from `.wait[data-ticket] time`.
- `ACTIONS` gives `awaiting-merge` `Open PR`, `awaiting-build` `Open spec`, `blocked` `Open issue`.
- `renderMerged()` draws compact cards with merged time, cost, tokens, `Spec`, `PR`. Merged entries carry no thread link (`api.ts` builds `threadLink` only for status rows, PM rows and the chief).
- `copyButton()` is shared by ticket cards, PM rows and the Chief of Staff card. It draws only `COPY_ICON`.
- `api.ts` gives the page `chief.threadLink` as `<t3-thread://v2/<environmentId>/<threadId>>`. `renderStatus()` does not receive it today.
- The `button[data-copy]` click handler already copies `data-copy` and shows `Copied` or `Copy failed` (text buttons swap their text; icon buttons swap label and title).
- #391, which would have removed the status and wait/next lines, was closed as not planned on 2026-11-15 after this ticket was written. #394 (PR link as soon as the PR exists) is still open and only changes when `prUrl` is set.

## T3 prefill: what exists

Checked by reading the installed T3 Code bundles on this machine: T3 Code (Nightly) `0.1.10-nightly.20261114.4695` (the running one) and T3 Code (Beta) `0.1.9`. Both register the `t3code` URL scheme and ship `promptLinkAppPath()` (`packages/shared/src/promptLinks.ts`):

- `t3code://threads/<environmentId>/<threadId>?prompt=<text>` routes to the thread `/<environmentId>/<threadId>` with the prompt.
- The renderer reads `prompt` (max 8000 characters, hidden-character check) and shows a "Open this prompt" step whose text is: "It opens as a draft. Nothing runs until you press Send."

So a prefill route exists, and it does not send. The environment and thread ids in our `t3-thread://v2/<env>/<thread>` link are the same two path parts. The build confirms it by clicking the link for real (see Test) and records the result in the PR.

## Design

### Card layout (`ticket()`, every band)

One template for every ticket card, compact or not:

1. **Top row**: `rowHead()` as today, with the thread copy button (below).
2. **Middle row** `<div class="actions">`, drawn only when it has something: the `Open PR` or `Open spec` link from `actionFor()`, then the approve controls. `blocked` no longer has an action: `Open issue` is removed from `ACTIONS` (the ticket number in the top row already links the issue).
3. **Bottom row** `.foot`: the Agents and Details control, then one `.meta` line: risk badge, `Spec`, `PR`, active time, cost, joined by ` · `, missing parts left out. Time and cost go in one `<span class="summary" data-ticket>` inside the meta so the tick loop keeps refreshing them. The `Other` group's stage phrase (today the last meta part on those compact cards) stays last.

The `status` sentence and the `wait`/`next` lines are no longer drawn on cards. `stageSentence()`, `waitText()` and the `.wait` tick refresh are removed if nothing else uses them; the `next` text stays in the Details panel, which is where a blocked card's reason is read now. The `compact`, `attn` and `blocked` classes stay, so the colored edges do not change.

Merged cards (`renderMerged()`) already match this shape: top row, no middle row, bottom row with merged time, cost, tokens, `Spec`, `PR`. They are left as they are; they have no thread link to copy.

### Thread copy button

`copyButton(link, { thread: true })` adds a small thread (speech bubble) glyph before the copy glyph inside the same `<button>`. Ticket cards pass `thread: true`; PM rows and the Chief of Staff card keep the plain icon (out of scope). Label and title stay `Copy thread link`, and the click still copies the link.

### Approve button

Shown on `awaiting-merge` and `awaiting-build` cards only, to the right of the `Open PR` / `Open spec` link.

- `approveCommand(r)` returns `approve <N>` where `N` is the number after the last `-` of the ticket id (`CW-402` gives `approve 402`), or null for any other stage or an id with no number.
- `promptLink(chiefThreadLink, text)` turns `<t3-thread://v2/<env>/<thread>>` into `t3code://threads/<env>/<thread>?prompt=<encoded text>`, or null when the link is missing or not that shape (both ids must match the same safe-id rule `api.ts` uses).
- With a prompt link, the button is `<a class="approve" href="t3code://...">Approve</a>`. Clicking it opens the Chief of Staff thread with `approve 402` in the input.
- Without one (no chief thread yet), it is `<button type="button" class="approve" data-copy="approve 402">Approve</button>`, and the existing copy handler shows `Copied` or `Copy failed`.
- A second `Changes` control works the same way with `changes <N>: ` (trailing space, for the user to type the change). Same row, same mechanism, no new layout.

`renderStatus()` gets the chief thread link as a new trailing argument, passed from the shell's `last.chief?.threadLink`.

Nothing in the page or server posts to T3. The link only opens T3; the user sends.

## Test

Per `AGENTS.md` § Testing, one table-driven test per rule in `page/app.test.js`:

- Card layout: for a Your turn, in progress, Up next, Not started, blocked and helper row, the rendered card has the top, optional middle and bottom rows in that order, the bottom row's meta holds risk, `Spec`, `PR`, time and cost in that order, and no `status`, `wait` or `next` line.
- Approve: per stage, `approve N` / `changes N: ` text, the `t3code://threads/...?prompt=` href with a chief link, the `data-copy` button without one, and no approve control for every other stage.
- `promptLink()`: a good link, a missing link and malformed links (wrong scheme, extra path part, unsafe id) in one table.
- Existing tests that assert the old row order, the `status`/`wait`/`next` lines or `Open issue` are updated.

By hand, in the build: open a `t3code://threads/<env>/<thread>?prompt=...` link for a throwaway thread (the build's own thread) and confirm the text lands in the input and is not sent. Record the T3 version in the PR. Clicking from the dashboard page itself, in the default browser and in T3's preview pane, goes under Not proven if it can't be done from the build.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | One card template; middle row; time and cost in the meta; thread glyph; `approveCommand()`, `promptLink()`; `renderStatus()` takes the chief link; drop `Open issue`, status, wait/next and their dead helpers. |
| `agent-team/scripts/dashboard/page/index.html` | `.actions` row and `.approve` styles; drop the rules only the removed lines used. |
| `agent-team/scripts/dashboard/page/app.test.js` | Updated and new tests above. |

## Non-goals

- Any change to an approval gate, `cos_user_check.py` or the `createdBy: "user"` check.
- Sending a message from the dashboard.
- Buttons for `cancel`, `hold` or `adopt`.
- PM rows, the Chief of Staff card, merged cards.
- #394 (when the PR link appears).

## Calls I made

- **I remove the status and wait/next lines in this ticket.** The ticket left that to #391, but #391 was closed as not planned after this ticket was written, and the acceptance asks for no other lines between the top and bottom rows. The live `waiting 3h 16m` counter goes away with them.
- **A blocked card's reason moves to the Details panel only.** With `Open issue` and the `next` line gone, the card itself no longer says why it is blocked; the red edge still marks it, and Details shows the `next` text.
- **The approve button is a `t3code://` link, not a clipboard copy,** because both installed T3 versions open a thread with a `prompt` as an unsent draft. Clipboard is only the fallback when the dashboard has no Chief of Staff thread link.
- **I add the `Changes` stub (`changes N: `).** Same link, same row, so it is cheap. The trailing space may be trimmed by T3; if so the user types it.
- **The thread glyph is on ticket cards only.** PM rows and the Chief of Staff card keep the plain copy icon, since the ticket keeps them out of scope.
- **The `Other` group's stage phrase stays,** last in the bottom row. Without it those cards would not say what stage they are in.
- **Merged cards are not changed.** They already have this shape and have no thread link.
- **`approve N` uses only the number** (`approve 402`, not `approve CW-402`), as in the ticket's example.
