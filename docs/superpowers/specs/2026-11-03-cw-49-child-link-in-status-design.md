# CW-49: Show the child thread link under the ticket in the status table

**Ticket:** [CW-49](https://github.com/dbeallor/collective-wisdom/issues/49)
**Status:** Shipped

## Goal

In the Chief of Staff's `status` answer, the link to a ticket's child thread sits under the ticket ID and title in the Ticket cell. Today it trails the Next cell, where it's easy to miss and makes that cell longer. The user should find the thread by looking at the ticket, not by reading to the end of the row.

## Non-goals

- The `Next` wording, the `Risk` cell, group order, and every other § Report format section (`Moving`, `Needs you`, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`), including their `<thread link>` lines.
- Links in the approval blocks (§ Approval requests).
- Any script. No script builds the status table; the Chief of Staff writes it from the skill.

## Today

Facts from `main` at `e835684`.

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Report format "Status layout" shows one table per group with Ticket, Risk and Next columns. All five example rows end their Next cell with `<thread link>`. The rules under the example don't mention the link at all.
- `where's <PREFIX>-N?` uses the same layout with one row (last rule in that list). A ticket not in state gets one line from the tracker instead of a row.
- Every ticket in state has a `childThreadId`: the `start` op requires it (`cos_state.py`), and a continuation start replaces it. A queued or blocked ticket keeps the thread of its last child.
- `agent-team/docs/agents/chief-of-staff.md` mentions the layout once ("answers `status` in the grouped table layout") and doesn't describe the columns.

## Design

### Example

Each example row moves `<thread link>` from the end of Next to a second line of the Ticket cell, joined with `<br>`:

```
| Ticket | Risk | Next |
|---|---|---|
| **<PREFIX>-197** CSV export<br><thread link> | High (touches auth) | PR #180, reviews PASS. Reply `approve 197` or `changes 197: …`. |
```

GitHub-flavoured markdown has no line break inside a table cell other than inline HTML, and GitHub renders `<br>` there. A client that strips inline HTML shows `<br>` as text or drops it; the row still reads on one line either way.

### Rule

Add one rule to the list under the example:

- The Ticket cell is `**<PREFIX>-N** title`, then `<br>` and the link to the ticket's child thread (`childThreadId` in state). A row with no `childThreadId` (or a null one) has no `<br>` and no link. The link is never repeated in Next.

The `where's <PREFIX>-N?` rule already says "the same layout", so its row picks this up. Add "with the thread link under the ticket" to that rule so it isn't missed. The one-line answer for a ticket not in state is unchanged: there is no child to link.

### Role doc

In `agent-team/docs/agents/chief-of-staff.md`, change "answers `status` in the grouped table layout" to "answers `status` in the grouped table layout, with each ticket's child thread link under its ID and title".

## Acceptance

- The Status layout example shows `<thread link>` under the ticket ID and title in every row, and no Next cell ends with `<thread link>`.
- The rules say the link comes from `childThreadId` and is left out when there is none.
- The example row, pasted into a GitHub comment preview, shows the link on its own line in the Ticket cell.

## Testing

Prose only. No test: AGENTS.md § Testing says not to test prose in skills. The plan's manual check renders one example row in a GitHub markdown preview (`./scripts/gh.sh api markdown` with mode `gfm`) and confirms the `<br>` comes through.

## Calls I made

- **A row in state always shows the link, whatever its stage.** The ticket says "only when the ticket has a running child thread (a `childThreadId` in state)". Every ticket in state has one, including queued and blocked tickets whose child is idle. I read the ticket's parenthesis as the test: show the link whenever `childThreadId` is set, since that thread is where the user would go to look. In practice the "no link" case only covers a hand-edited or damaged state entry.
- **`<br>` for the line break.** It is the only way to break a line in a GFM table cell. Two trailing spaces or a blank line end the table. I haven't confirmed that T3 Code's chat renders `<br>` in a table; the build checks it in a real `status` reply if a browser is available, and lists it under checks that didn't run if not.
- **The link text stays `<thread link>`,** the same placeholder the rest of the skill uses. The skill doesn't say elsewhere how to word the link, and this ticket doesn't change that.
- **Other report sections keep their trailing links,** for example `- <PREFIX>-202 blocked: <one line>. <thread link>` under `Needs you`. The ticket's out-of-scope list keeps them as they are.
- **No install PR in this ticket.** The ticket ends in a collective-wisdom PR plus an install PR in the app; the install PR is the app's own follow-up, as for every shared-file change.
