# As-built: compatibility document

**Shipped:** in PR #224
**Ticket:** CW-223
**Spec:** [2026-11-08-cw-223-compatibility-matrix-design.md](../specs/2026-11-08-cw-223-compatibility-matrix-design.md)

## Differs from the spec

- The spec had each non-`works` cell carry a ticket link or `none yet`. Cells carry a short reason and a gap number (`G1` to `G16`), and the Gaps list holds the ticket line for each, all `none yet`. This keeps the tables narrow.
- Local dashboard on Claude Code alone, Codex alone and Cursor stays `not supported`, but the reason is that it shows Chief of Staff state, which needs T3 Code, not that it needs a T3 pane.
- Local dashboard on Codex in T3 Code is `partial`: no gantt rows or spend.
- `status-pane` on Claude Code alone is `partial`, not `works`: its ticket groups come from `state.json`, which only a Chief of Staff writes.
- `agent-gantt` on Claude Code in T3 Code stays `untested`; the reason names hooks that read T3 sessions with the pane not seen in T3.
- Notes under the tables add that a Codex or Cursor child's cost is unknown to `no_hands.py`, so a No Hands run stops.
