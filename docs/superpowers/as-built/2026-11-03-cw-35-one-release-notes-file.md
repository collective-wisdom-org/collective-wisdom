# As-built: One release notes file on GitHub

**Shipped:** in PR #37
**Ticket:** CW-35 (#35)
**Spec:** [2026-11-03-cw-35-one-release-notes-file-design.md](../specs/2026-11-03-cw-35-one-release-notes-file-design.md)

## What shipped

- The spec, plan and index for the research ticket.
- One comment on #35 comparing six options and recommending that the merge step write the combined file to a separate `release-notes` branch. `release_notes.py` and the `merge_pr.py` check stay as they are.

## Differs from the spec

Nothing.

## Verification

`python3 -I -m pytest -q agent-team/scripts` passes (327 tests). The diff touches only `docs/superpowers/`; no skill, script or role doc changed.
