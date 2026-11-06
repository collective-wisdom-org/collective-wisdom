# As-built: CW-52 GitHub merge gate

**Shipped:** in PR #84
**Ticket:** CW-52
**Spec:** [2026-11-04-cw-52-github-merge-gate-design.md](../specs/2026-11-04-cw-52-github-merge-gate-design.md)

## Differs from the spec

- The owner login is compared case-insensitively (GitHub logins are), not exactly.
- `read_facts` reads branch protection only for an open PR, so a rerun on an already merged PR needs no protection read.
- `merge-pr` and `ship-loop` § Team mode add a rule the spec doesn't state: never submit a GitHub review under any login, since the owner's approval is now the merge proof.
