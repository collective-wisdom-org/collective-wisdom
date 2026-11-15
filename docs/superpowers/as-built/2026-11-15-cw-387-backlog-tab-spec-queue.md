# As-built: Move the dashboard Backlog to its own tab and show a spec queue

**Shipped:** in PR #407
**Ticket:** CW-387
**Spec:** [2026-11-15-cw-387-backlog-tab-spec-queue-design.md](../specs/2026-11-15-cw-387-backlog-tab-spec-queue-design.md)

## Differs from the spec

- The spec says `renderBacklog(groups, collapsed, backlogPage)`. It also takes optional `open` and `info` sets, so a Backlog row's open Agents or Details panel stays open through the 5-second redraw.
- The spec leaves `renderStatus` unchanged for an empty list. It now returns "No state yet" when the only group is Backlog, so the Ship loop tab is not blank.
- A `spec-queued` row still reads "Waiting for a spec slot". It is keyed on the Waiting to spec group instead of `Other`.
- `groups.ts` exports a `GROUP_ORDER` list that `api.ts` uses to place the Waiting to spec group.
- README's dashboard section changed too: three bands, no Not started, a Backlog tab.
