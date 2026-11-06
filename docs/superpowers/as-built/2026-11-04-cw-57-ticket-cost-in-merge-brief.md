# As-built: Put the cost of each ticket in the merge brief

**Shipped:** in PR #81
**Ticket:** CW-57
**Spec:** [2026-11-04-cw-57-ticket-cost-in-merge-brief-design.md](../specs/2026-11-04-cw-57-ticket-cost-in-merge-brief-design.md)

## Differs from the spec

- A malformed ID (not like `CW-57`) exits 2 with argparse's usage message, not the `agent_usage: no transcripts for <ID>` line. That line is for a well-formed ID with no sessions.
- The line says `1 child run` for one run, not `1 child runs`.
- `cos_brief.py pr` prints `cost: cost $14.20 ...` (the label plus the script's line). The merge block's `Cost:` line starts at the first `$`.
- A continuation child is recognised by `TEAM MODE. CONTINUE` anywhere in its first message, since the real task has a preamble before it.
- `read_session` ignores a line whose timestamp can't be parsed when it builds the time span. Only the span skips such a line; a bad timestamp on a user or usage line still raises, as on main.
