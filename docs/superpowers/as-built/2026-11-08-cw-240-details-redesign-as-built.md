# As-built: CW-240 dashboard Details redesign

**Shipped:** in PR #244
**Ticket:** CW-240
**Spec:** [2026-11-08-cw-240-details-redesign-design.md](../specs/2026-11-08-cw-240-details-redesign-design.md)

## Differs from the spec

- The spec says entries dropped from `want` leave the PR cache at once. A PR read now stays in the cache until it is a minute old, so two tabs on different merged pages do not make each other read again.
- A merged want is keyed `<id>#<pr>`, so two merged PRs of one ticket keep their own text. A merged want for an id still on the board is ignored: the board ticket keeps its own detail.
- Every PR read asks for `body,files,comments,mergeCommit`, open or merged, because they share one cache.
- A click on the merged pager also triggers a poll, so the new page's text arrives without waiting for the next tick.
