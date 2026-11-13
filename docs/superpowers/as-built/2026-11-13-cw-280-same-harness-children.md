# As-built: Keep Chief of Staff children on its own harness

**Shipped:** in PR #291
**Ticket:** CW-280
**Spec:** [2026-11-13-cw-280-same-harness-children-design.md](../specs/2026-11-13-cw-280-same-harness-children-design.md)

## Differs from the spec

- A `harness-mismatch` line is reported on every pass while the mismatch lasts, not once per ticket, because state has no place to remember that a report was made.
- The `chief-provider` and `harness-mismatch` lines are printed in every look plan except the `start` trigger. A new repo's start plan must begin `follow startup.md § Setup`, and startup step 3 and Resume mode already save `chiefProvider`.
- The Codex and Antigravity subsections are a Provider id line plus one sentence saying every row is `not routed yet`, not full ten-row tables.
- The test for the start case is a separate small test beside the table test.
