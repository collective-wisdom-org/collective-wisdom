# WISE-484: Show only the red blocked x on dashboard cards, not the green check

**Status:** Shipped
**Ticket:** [#484](https://github.com/collective-wisdom-org/collective-wisdom/issues/484)
**Shipped:** in PR #486, as specified

## Goal

A dashboard card shows the blocked icon only when the ticket has an open blocker. Unblocked cards stop showing a green check, so the red x stands out.

## Today

- `marksColumn` in `agent-team/scripts/dashboard/page/app.js` (added by WISE-482) builds the marks column: the owner avatar slot, the epic slot (empty without an epic) and the blocked slot. The blocked slot holds a red x (`mark blocked`) when `r.blockedBy` has entries, else a green check (`mark clear`, tooltip `Not blocked`).
- `page/index.html` styles `.mark.clear` green. Each `.slot` is 20px high.
- `blockedBy` holds open blockers only (`backlog.ts` drops closed ones), so "only closed blockers" already reaches the page as an empty array.
- `page/app.test.js` test `marks column: ...` has a `green check` case.

## Change

1. `marksColumn`: when `blockedBy` is an empty array, the blocked slot is drawn empty (`<span class="slot"></span>`), the same way the epic slot is drawn empty without an epic. The red x branch is unchanged. Remove the `mark('clear', 'Not blocked', ...)` branch and update the doc comment.
2. `page/index.html`: remove the `.mark.clear` rule.
3. `page/app.test.js`: replace the `green check` case with a `no open blocker` case (`blockedBy: []`, with an epic) that asserts the epic tooltip is there, the output has no `mark clear`, no `mark blocked` and no `Not blocked`, and it still has 3 slots. Add a case with no epic and no blocker (`blockedBy: []`) that also has 3 slots and no blocked icon. The other cases are unchanged.

A row with no `blockedBy` and no `epic` (no relations read) still draws the bare avatar.

## Leaves out

- The epic icon, the avatar and the `blocked` stage styling.
- How relations are read (`backlog.ts`, `api.ts`).

## Calls I made

- **The empty blocked slot stays.** The ticket says the avatar and epic must not shift. Keeping the 20px slot, empty, means every card with relations keeps the same marks column height whether or not it is blocked, so cards don't change height when a blocker opens or closes. The cost is a blank 20px under the epic slot on unblocked cards. Dropping the slot would also leave the avatar and epic in place (the column fills top down) but would make blocked cards taller than unblocked ones.
- **No epic and no blocker still draws the marks column** (avatar plus two empty slots), not the bare avatar, so the avatar sits in the same place on every card that has relations.
