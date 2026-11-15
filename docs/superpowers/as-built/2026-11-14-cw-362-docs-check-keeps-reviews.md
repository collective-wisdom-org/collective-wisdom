# As-built: Keep the code and security reviews when only the docs check changed the head

**Shipped:** in PR #377
**Ticket:** CW-362
**Spec:** [2026-11-14-cw-362-docs-check-keeps-reviews-design.md](../specs/2026-11-14-cw-362-docs-check-keeps-reviews-design.md)

## Differs from the spec

- The spec says living-doc entries match the way `is_docs` does. Entries match case-sensitively: a case variant of a living path is a different file and gets `changed`. The hands-path check still uses `approval_policy.on_hands_path`'s own normalisation.
- The `Living docs to search:` line is read only from the `## Docs check` section of `project.md`, and a missing line, no backticked entry, or a missing issue prefix gives `changed`.
- `project_config.living_docs()` is new, built on a new `_committed_text`; the existing rows reader behaves as before. It has its own test table, which the spec did not list.
- The `pr_diff_delta` tests use a real temporary git repo with an injected living-docs config, not a fake `run`.
- `ship-loop` phase 4 says only that `note` also covers the docs check's living-docs-only fix commit, and points to `open-pr` for the conditions.
- Added in review: the `living` rule also refuses a file the fix commit adds or deletes (present at one head and absent at the other). Editing in place passes, including a file the PR added earlier. The spec did not say this.
