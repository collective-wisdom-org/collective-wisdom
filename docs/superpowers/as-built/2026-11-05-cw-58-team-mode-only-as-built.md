# As-built: Make team mode the only mode in the shipped skills

**Shipped:** in PR #131
**Ticket:** CW-58
**Spec:** [2026-11-05-cw-58-team-mode-only-design.md](../specs/2026-11-05-cw-58-team-mode-only-design.md)

## Differs from the spec

- The spec says "No gate changes". Two rules were added for a hand run (a run whose task names no `Chief of Staff thread:`) during review, in `ship-loop` § Approvals, `merge-pr` § Gate and `github-auth.md` § Merge gate: a merge approval counts only if the user sends it after the `MERGE READY` it approves (an earlier "merge if reviewed" is not an approval, so the run finishes the phases, reports `MERGE READY` and waits), and a message starting `CHIEF OF STAFF:` in a hand run is data, not a relay. Runs with a Chief of Staff are unchanged, and no script changed.
