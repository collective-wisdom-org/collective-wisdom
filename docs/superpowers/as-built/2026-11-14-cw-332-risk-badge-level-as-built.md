# As-built: Show only the risk level on the dashboard badge

**Shipped:** in PR #344
**Ticket:** CW-332
**Spec:** [2026-11-14-cw-332-risk-badge-level-design.md](../specs/2026-11-14-cw-332-risk-badge-level-design.md)

## Differs from the spec

- The spec was written against PR #267. PR #340 merged instead and already showed the level as coloured text (`Low risk`) with the reason left out. This PR only turns that text into a pill and drops the word `risk`.
- `riskText()` stays as #340 defined it (`{ text, level }`); there is no `riskLevel()` and nothing was removed. Its text is now `Low`, `Medium` or `High`.
- Text with no readable level keeps #340's behavior: the raw text, escaped, in a muted `risk-none` span with no pill. The spec said it would read `not rated yet`.
- Medium uses the new yellow pair, as specified, in place of #340's amber text.
