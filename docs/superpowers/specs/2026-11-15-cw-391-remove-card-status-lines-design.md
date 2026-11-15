# CW-391: Remove the status and next lines from dashboard cards

**Status:** Draft
**Ticket:** [#391](https://github.com/collective-wisdom-org/collective-wisdom/issues/391)
**Related:** #370 (row cards)

## Goal

A dashboard ticket card goes from its meta line (risk badge, `Spec` and `PR` links) straight to its footer (Agents and Details buttons and the summary), with no status sentence, wait counter or next line between them. A blocked row still says why it is blocked.

## Today

Facts from main at `5cd8e74`, in `agent-team/scripts/dashboard/page/`.

- `ticket()` in `app.js` draws a card as: head, `<div class="meta">`, then `<p class="status">` (from `stageSentence()`, left out for stages in `SECTION_STAGES`), then a note (`<p class="wait">` with a live `waitText()` counter while the stage starts with `awaiting-`, else `<p class="next">` with `r.next`), then `<a class="action">` from `actionFor()`, then the footer.
- A flat row (`compact`) skips all three lines and puts the stage sentence in its meta line in the `Other` group. A blocked row in a flat list is not compact: it is laid out as a card, red-edged (`li.row.blocked`), and its why is the `next` text (for example `Waiting on Dana`).
- The poll loop in `app.js` refreshes `.wait[data-ticket] time` once a minute with `waitText()`.
- `index.html` styles `.status`, `.next`, `.wait` and `li.blocked .status`.
- `stageSentence()` is also used for the compact row's meta phrase. `ageWords()` is also used by the Project manager's `read-age` line. The Details panel shows `Next` and `Stage` facts of its own.

## Design

### Cards

`ticket()` stops drawing `<p class="status">` and the wait or next note on a card. The action link (`Open PR`, `Open spec`, `Open issue`) stays where it is, between the meta line and the footer, so a card whose stage needs the user still offers it.

### Blocked rows

A blocked row keeps its card layout and red edge, and keeps two things so it still says why:

- Its meta line carries the stage sentence (`Blocked. Needs an answer from you`) as a compact `Other` row's does today, through the same `phrase` path.
- It keeps `<p class="next">` with its `next` text, which is where the why lives. Only a blocked row draws it.

Its `Open issue` action stays.

### Removed code

- `waitText()` and its export, the `.wait` refresh in the poll loop, and the `SECTION_STAGES` set (only the status line read it).
- CSS: `.status`, `.wait` and `li.blocked .status`. `.next` stays for the blocked row.
- `stageSentence()` and `ageWords()` stay: other code calls them.

### Tests

In `app.test.js`:

- The tests that assert `<p class="status">` on cards and the `waitText` and wait-counter tests go. In their place one table-driven test renders a card per stage (`awaiting-merge`, `awaiting-build`, `build`, `merge`, an unknown stage, with `next` and `stageAt` set) and asserts no `class="status"`, `class="wait"` or `class="next"` appears, and that the action link still appears for `awaiting-merge` and `awaiting-build`.
- The blocked-row test keeps asserting the sentence and `<p class="next">Waiting on Dana</p>`, now with the sentence in the meta line.
- `stageSentence` keeps its table test.

## Leaves out

- The risk badge, the `Spec` and `PR` links, the Agents and Details panels, and the `Next` fact inside the Details panel.
- The wait time: it goes from the card with nothing in its place. The Details panel is not given a new `Waiting` fact.

## Calls I made

- A blocked row keeps its `next` line. The ticket allowed moving the why elsewhere; keeping it on the row is the smallest change and the why is what the user needs to answer.
- The blocked row's `Blocked. Needs an answer from you` sentence moves into its meta line instead of being dropped, so the row still reads as blocked next to the red edge.
- The live waiting counter is dropped outright, not moved to the Details panel or the meta line. The ticket lists it as one of the lines to remove.
- The action link stays below the meta line, as the ticket's acceptance asks, rather than moving into the footer.
- The `SECTION_STAGES` set goes with the status line, since nothing else reads it.

## Verification

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes (Node 24 or newer).
- `python3 -I -m pytest -q agent-team/scripts` passes.
