# As-built: Stamp status-line and approval-comment times from the clock

**Shipped:** in PR #403
**Ticket:** CW-385
**Spec:** [2026-11-15-cw-385-clock-stamped-times-design.md](../specs/2026-11-15-cw-385-clock-stamped-times-design.md)

## Differs from the spec

- The spec rejects a hand-typed `since <digit>` time "before the first `"`". It shipped as "before the first `: `", the end of the `<stage> since {since}` prefix. The quote rule also rejected a `Risk:` reason such as `unchanged since 2024`, which the Chief of Staff must carry into every later status line.
- The state-file example status in `state-keys.md` shows a stamped time, not `{since}`, because it shows a stored file.
