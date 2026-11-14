# CW-324: Show only the stage and the time it began on dashboard ticket cards

**Status:** Draft
**Ticket:** [#324](https://github.com/collective-wisdom-org/collective-wisdom/issues/324)

## Goal

A dashboard ticket card stops showing the free-text status line the Chief of Staff writes. Each card shows `<stage> since HH:MM` beside its spec and PR links instead, in every group, where the time is when the ticket entered that stage.

## Today

Facts from `main` at `8ddace1`.

- `status` in `.agent-team/state.json` is free text, set by every `stage` op (`op_stage` in `agent-team/scripts/cos_state.py:241`).
- `row()` in `agent-team/scripts/dashboard/groups.ts` splits `status` at `Risk:` into `next` and `risk`. `buildApi` in `dashboard/api.ts` puts both on each `StatusRow`, with `stage`.
- `ticket()` in `dashboard/page/app.js:192` draws `next` as `div.next` on a card, or a span in the `sub` line of a flat row (the Queued band). It draws the stage badge only in the `Other` group. `renderDetails` shows `next` as the `Next` fact.
- No ticket key records when the ticket entered its stage. `queuedAt` is set only in `*-queued` stages and `lastSeenAt` is the approval cut-off in four stages; neither can stand in.
- `op_start` creates a ticket in `spec`; it never goes through `op_stage` for that first stage.
- `clock(ms)` in `app.js` prints local `HH:MM`.

## Design

1. **New ticket key `stageAt`**, a UTC time like the others (`now()`). Added to `TICKET` in `cos_state.py`.
   - `op_start` sets it, since it puts the ticket in `spec`.
   - `op_stage` sets it when the new stage differs from the old one. A `stage` op to the same stage (a status rewrite, a new head) leaves it.
   - Not settable by hand: a `set` or `stage` op that names `stageAt` is rejected, the way `lastSeenAt` is in its stamped stages, so the time always means what the card says.
   - A ticket written before this change has no `stageAt`. Nothing backfills it.
2. **API.** `StatusRow` gets `stageAt?: string`, copied from the ticket in `buildApi` when it is a string. Helper and Todo/Backlog rows get none.
3. **Card.** In `ticket()`:
   - Drop `next` from both the card and the flat row.
   - The `sub` line starts with a stage span for every row that has a `stage`, in every group: `<stageWords(stage)> since HH:MM`, using `clock()` on `stageAt`. With no `stageAt`, or one that does not parse to a time, it shows the stage name alone. It keeps the `badge stage` class the `Other` group uses today.
   - The risk badge, spec link, PR link, `blocked` card class and copy icon stay as they are.
4. **Docs.** `chief-of-staff/state-keys.md`: add `stageAt` to the example ticket and a one-line key entry (stamped by the script on a stage change and by `start`, rejected in a `set`, shown on the dashboard card).
5. **Tests**, table-driven, in existing files:
   - `test_cos_state.py`: one table over `start`, a stage change, a same-stage `stage` op with new `status`, and a `set` naming `stageAt` (rejected), checking whether `stageAt` changed.
   - `page/app.test.js`: `renderStatus` on a non-`Other` group row with `stageAt` and `next` shows the stage and `since HH:MM` and none of the `next` text; a row without `stageAt` shows the stage name and no `since`.
   - `api.test.ts`: the existing `buildApi` row test also checks `stageAt` passes through.

## Leaves out

- The risk badge and the `Risk:` parsing.
- The `Next` fact in Details: it stays, so the status text is still one click away.
- `status` in state.json and `cos_state.py show`.
- Rewording the status lines the Chief of Staff writes.
- Backfilling `stageAt` for tickets already in state.
- A date for a stage that began on an earlier day.

## Calls I made

- **HH:MM only, no date.** The ticket names `clock()`, which has no date, so a ticket that has sat in `awaiting-merge` since yesterday 16:00 reads `since 16:00`. The full time is not shown anywhere else on the card.
- **`start` stamps too.** The ticket says `op_stage`; without `op_start` a new ticket's first stage, `spec`, would never get a time.
- **`stageAt` can't be set by hand.** The ticket doesn't say; a hand-set time could make the card lie.
- **Name `stageAt`**, matching `queuedAt` and `lastSeenAt`.
- **Stage text is the badge.** Each card's stage reads like the `Other` group's badge today, with `since HH:MM` added inside it, rather than as plain text.
- **No time, no `since`.** An old ticket or a bad value shows the stage name without a time, not a dash or "unknown".
