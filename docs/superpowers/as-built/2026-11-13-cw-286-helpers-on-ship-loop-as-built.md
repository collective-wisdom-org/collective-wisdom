# As-built: Show ticket helpers on the Ship loop tab and count their time in the ticket gantt

**Shipped:** in PR #289
**Ticket:** CW-286
**Spec:** [2026-11-13-cw-286-helpers-on-ship-loop-design.md](../specs/2026-11-13-cw-286-helpers-on-ship-loop-design.md)

## Differs from the spec

- The spec lists an issue with `status:todo` as Todo. A ticket is Todo only when `status:todo` is its sole `status:` label; an issue that also carries another `status:` label is not listed.
- The spec caches each author's permission answer for the life of the server. A team role is cached that long; a non-team answer or a failed call is cached for 5 minutes, so a transient failure does not hide an author for good.
