# As-built: Show the share of a subscription used next to the dollar cost of a ticket

**Shipped:** in PR #143
**Ticket:** CW-135
**Spec:** [2026-11-05-cw-135-subscription-usage-percent-design.md](../specs/2026-11-05-cw-135-subscription-usage-percent-design.md)

## Differs from the spec

- The spec says the test uses a $14.20 ticket and a $0.50 ticket. The existing fixture ticket costs $19.20, so the test extends `test_ticket_line` and checks `0.16%` for `12000`, and `<0.01%` for a usage of `1000000`. `0.12%` for $14.20 is checked by hand in the PR proof.
- The row's text is "The API-equivalent dollars the Claude plan shows. Ticket costs then show a share of it" (template: "Set it to the API-equivalent dollars the Claude plan shows (a number such as 12000); ticket costs then show a share of it").
- `<0.01%` prints when the share rounds below `0.01` (under 0.005%), so 0.005% to 0.01% prints `0.01%`.
