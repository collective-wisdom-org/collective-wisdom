# As-built: Sort release notes by PR merge time

**Shipped:** in PR #83
**Ticket:** CW-41
**Spec:** [2026-11-04-cw-41-release-notes-merge-order-design.md](../specs/2026-11-04-cw-41-release-notes-merge-order-design.md)

## Differs from the spec

- A file note that was renamed after it merged (CW-27 and CW-28, renamed in #29) gets no merge time, because `git log --diff-filter=A` doesn't count a rename as an add. It prints without a `Merged` line and sorts by heading date and file name, as the spec's fallback says. Counting renames would stamp it with the rename PR's time instead.
- The order test has three rows (file name against merge time; PR and file note on one day; untimed fallback). The untimed-order and undated-warning rows stay in the existing test, run with the git lookup stubbed empty. A separate test checks that a failing git call gives an empty lookup.
