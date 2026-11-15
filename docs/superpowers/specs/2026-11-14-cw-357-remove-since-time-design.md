# CW-357: Remove "since HH:MM" from dashboard ticket cards

**Status:** Draft
**Ticket:** [#357](https://github.com/collective-wisdom-org/collective-wisdom/issues/357)
**Runs beside:** CW-354, CW-349 and CW-350, which also edit the dashboard page. This change keeps to the `since` text so a rebase stays small.

## Goal

No ticket card or row on the dashboard shows "since HH:MM". Where the status line only repeated the section name with that time, it goes too.

## Today

Facts from main at `81c114b`, all in `agent-team/scripts/dashboard/page/app.js`.

- `since(stageAt)` returns ` since HH:MM` when `stageAt` parses.
- `stageSentence(stage, stageAt)` maps a stage to a sentence (`Building`, `Writing the spec`, `Waiting for a build slot`, ...) and adds `since(stageAt)` for every stage but `awaiting-*`.
- `ticket()` draws that sentence as `<p class="status">` on every card (bands Your turn and In progress).
- A flat row (band Up next) puts a phrase in its meta line: `stageSentence(...)` in the `Other` group, else `<group label> since HH:MM` (`Waiting to build since 09:05`). Not started rows are `slim` and show no phrase.
- `stageAt` also feeds `waitText` (the `waiting 3h 16m` counter on `awaiting-*` cards) and its `Since <date time>` tooltip.

## Design

### `app.js`

- Delete `since()`.
- `stageSentence(stage)` takes only the stage and returns the sentence with no time. Same mapping as today; an unknown stage still shows its slug with spaces.
- Cards: add a set `SECTION_STAGES` of `build`, `build-queued`, `spec`, `spec-queued`, `merge`, `merge-queued`. A card whose stage is in it draws no `<p class="status">`. Every other stage (`awaiting-*`, `blocked`, an unknown stage) keeps the sentence, with no time.
- Flat rows: the meta phrase is `stageSentence(r.stage)` in the `Other` group and nothing elsewhere. The meta line keeps the id, risk and PR link.
- Unchanged: `stageAt`, `waitText`, the waiting counter and its `Since` tooltip, the `Stage` fact in Details.

### `app.test.js`

- The `stageSentence` table drops `stageAt` and has no time suffix. Its `renderStatus` check becomes: a `build` card has no status line, an `awaiting-merge` card has one.
- The band test's queued row meta line ends after the risk badge, with no `Waiting to build since 09:05`.
- One table-driven check over `renderStatus` for each group name the page knows (cards and flat rows, with `stageAt` set): no output matches `since \d\d:\d\d`. That is the acceptance rule, and it fails if any path adds the time back.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | Delete `since()`, simplify `stageSentence`, skip the section-repeat status line, drop the flat row group phrase. |
| `agent-team/scripts/dashboard/page/app.test.js` | Update the pinned text; add the no-`since` table. |

## Non-goals

- Removing `stageAt` from `state.json` or the API.
- Changing the waiting counter or its tooltip.
- Any other card or row markup (CW-354 owns the row markup changes).

## Calls I made

- **An unknown stage keeps its status line.** The ticket lists the six stages to drop; a stage the page does not know shows its slug, which is the only clue to what it is, so it stays.
- **`awaiting-review` keeps its sentence** ("Waiting for a teammate's review"). It is an `awaiting-*` stage, which the ticket keeps.
- **`stageSentence` loses its `stageAt` argument** instead of ignoring it, so no caller can pass a time expecting it to show.
- **The empty `<p class="status">` is left out, not drawn blank,** so a building card has no gap between its meta line and its agent text.
- **No CSS change.** The `.status` rule stays for the cards that still draw it.
