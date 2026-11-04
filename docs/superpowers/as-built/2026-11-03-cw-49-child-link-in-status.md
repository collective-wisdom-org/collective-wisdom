# As-built: Child thread link under the ticket in the status table

**Shipped:** in PR #61
**Ticket:** CW-49 (#49)
**Spec:** [2026-11-03-cw-49-child-link-in-status-design.md](../specs/2026-11-03-cw-49-child-link-in-status-design.md)
**Plan:** [2026-11-03-cw-49-child-link-in-status.md](../plans/2026-11-03-cw-49-child-link-in-status.md)

## What shipped

- `chief-of-staff` § Report format "Status layout": the five example rows carry `<br><thread link>` in the Ticket cell and no link in Next. A new rule says the link is the ticket's `childThreadId` and is left out when there is none. The `where's <PREFIX>-N?` rule names the link under the ticket.
- `docs/agents/chief-of-staff.md` says `status` shows each ticket's child thread link under its ID and title.

## Differs from the spec

- Nothing.

## Checks

- `uvx pytest -q agent-team/scripts`: 419 passed.
- GitHub's markdown API keeps the `<br>` inside the Ticket cell. T3 Code's chat was not checked.
