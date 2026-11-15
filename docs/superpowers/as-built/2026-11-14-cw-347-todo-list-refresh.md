# As-built: Show a Todo or Backlog change on the dashboard right away

**Shipped:** in PR #356
**Ticket:** CW-347
**Spec:** [2026-11-14-cw-347-todo-list-refresh-design.md](../specs/2026-11-14-cw-347-todo-list-refresh-design.md)

## Differs from the spec

- The spec says the stamp is the time in UTC. It ships to the millisecond, so two changes in one second differ.
- The spec says a bad `tracker-lists.json` shows on the page on every tracker. On GitHub the file is read only for the stamp, so a bad file there shows nothing.
- On Linear and Jira a failed `list-tickets` call is reported only in the Chief of Staff's reply (`Dashboard not refreshed: ...`). The dashboard keeps the old lists and shows no message for it; it shows a message only for a bad saved file.
