# As-built: compatibility document

**Shipped:** in PR #224
**Ticket:** CW-223
**Spec:** [2026-11-08-cw-223-compatibility-matrix-design.md](../specs/2026-11-08-cw-223-compatibility-matrix-design.md)

## Differs from the spec

- The spec had each non-`works` cell carry a ticket link or `none yet`. Cells carry a short reason and a gap number (`G1` to `G16`), and the Gaps list holds the ticket line for each, all `none yet`. This keeps the tables narrow.
- Local dashboard on Claude Code alone, Codex alone and Cursor stays `not supported`, but the reason is that it shows Chief of Staff state, which needs T3 Code, not that it needs a T3 pane.
- Local dashboard on Codex in T3 Code is `partial`: no gantt rows or spend.
- `status-pane` on Claude Code alone is `partial`, not `works`: its ticket groups come from `state.json`, which only a Chief of Staff writes.
- Notes under the tables add that a Codex or Cursor child's cost is unknown to `no_hands.py`, so a No Hands run stops.
- Ship loop by hand on Codex alone and Cursor is `partial`, not `untested`: the CI wait needs `t3_background_wait`, as on Claude Code alone.
- `agent-gantt` on Claude Code in T3 Code is `partial`, not `untested`: its hooks run in T3 sessions and feed the dashboard's gantt rows, and only the pane in T3 is unseen.
- The legend lets `works` rest on a run the team does today, with unrecorded runs named in a note (the Linear cells), instead of requiring a recorded verification.
