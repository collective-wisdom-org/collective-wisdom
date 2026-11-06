# As-built: status pane

**Shipped:** in PR #146
**Ticket:** CW-144
**Spec:** [2026-11-05-cw-144-status-pane-design.md](../specs/2026-11-05-cw-144-status-pane-design.md)

## Differs from the spec

- The install test is an extra row in the existing table in `agent-team/scripts/test_install.py`, not a new `test_status_pane.py`.
- State has no title field (`cos_state.py` rejects a `title` key), so a row shows the ticket ID alone; the mod draws a title only when state holds one.
- Queued groups sort by each ticket's `queuedAt`, because state has no `queue` key. That is the order `cos_state.py show` prints.
- The subagent list is everything `$.agent.list()` returns; the mod adds no session filter of its own.
- The root `docs/agents/status-pane.md` is a link to the shared doc, which `test_root_links.py` requires for every shared doc.
- The mod reads the state file at the root checkout, found with `git rev-parse --path-format=absolute --git-common-dir`, and falls back to the relative path when that fails.
- A pane that was already open reopens on `session.start` even with `autoOpen` off, so a reload does not stop the refresh.
- The 5-second timer stops when the pane is closed.
