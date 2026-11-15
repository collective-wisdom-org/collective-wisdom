# CW-390 plan: flip the dashboard collapse chevrons

Spec: `docs/superpowers/specs/2026-11-15-cw-390-flip-collapse-chevrons-design.md`

## Task 1: `agent-team/scripts/dashboard/page/index.html`

1. In the collapsed rules (`summary::after` and `summary.band-head > h2::after`) set `transform:rotate(-135deg)` and `vertical-align:-.05em`.
2. In the open rules (`details[open] > summary::after` and `details[open] > summary.band-head > h2::after`) set `transform:rotate(45deg)` and `vertical-align:.12em`.
3. Leave the box, borders, margin and `transition` as they are. No test (styling).

## Verify

Run the dashboard test command from `AGENTS.md`, then render the page and screenshot a collapsed and an open group and band in light and dark for the PR proof.
