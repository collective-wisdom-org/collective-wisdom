# As-built: Review mode setting that uses CI review instead of the agent reviewers

**Shipped:** in PR #137
**Ticket:** CW-126
**Spec:** [2026-11-05-cw-126-ci-review-mode-design.md](../specs/2026-11-05-cw-126-ci-review-mode-design.md)

## Differs from the spec

- The template's `CI review bot login` row gives its example in words, with no backticks. The scripts read the first backticked token, so the spec's `some-review-bot` example would have read as a configured bot in an unedited template.
- `ci_review.py list` prints `?`, `(unreadable path)`, `(no url)` or `(bad id)` for an unresolved thread whose line, path, URL or id fails its pattern check, and still counts it as unresolved. `resolve` does not check the mode. `ci_review.py` takes `--help`.
- `cos_ready_check.py` in `ci` mode prints `building ABC-N #PR (CI checks not green)` for a build ticket whose checks are not all green.
- The `ci:` line in the brief and handoff shows the full head SHA.
