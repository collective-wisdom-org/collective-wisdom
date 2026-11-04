# As-built: Set up the collective-wisdom-builder GitHub user

**Shipped:** in PR #67
**Ticket:** CW-65 (#65)
**Spec:** [2026-11-04-cw-65-builder-gh-user-design.md](../specs/2026-11-04-cw-65-builder-gh-user-design.md)
**Plan:** [2026-11-04-cw-65-builder-gh-user-plan.md](../plans/2026-11-04-cw-65-builder-gh-user-plan.md)

## What shipped

- `docs/agents/project.md`: the Builder login row is `collective-wisdom-builder`. The cell's note is unchanged.
- The PR was opened with `AGENT_GH_ROLE=builder`, and its author is `collective-wisdom-builder`.

## Differs from the spec

Nothing.

## Checks

- Builder token on `repos/dbeallor/collective-wisdom`: `push: true`.
- Verify block from `docs/agents/github-auth.md`: `builder` prints `collective-wisdom-builder`, `chief-of-staff` prints `collective-wisdom-chief`, `code-reviewer`, `security-reviewer` and no role print `dbeallor`.
- No open PR had a `Head moved to` note to repost.
- `python3 -I -m pytest -q agent-team/scripts`: 496 passed.
