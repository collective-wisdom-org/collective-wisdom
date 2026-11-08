# As-built: T3 Code harness columns in the compatibility document

**Shipped:** in PR #229
**Ticket:** CW-226
**Spec:** [2026-11-08-cw-226-compat-t3-columns-design.md](../specs/2026-11-08-cw-226-compat-t3-columns-design.md)

## Differs from the spec

- Every cell in Matrix 1 and Matrix 2 starts with a colored circle (green works, yellow partial, red not supported, white untested), and so do the legend rows. The user asked for cell colors, and markdown tables have none, so the circle is a visual aid and the word stays the source of truth.
- Matrix 2 gains an Azure DevOps (ADO) column, meaning Azure Boards for tickets with code on GitHub. The spec left Matrix 2 alone. The repo has no Azure DevOps support, so every ADO cell is not supported, and the new gap `G19` records that there is no adapter. A Full compatibility line and a note under Matrix 2 were added with it.
