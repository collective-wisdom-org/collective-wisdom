# One release notes file on GitHub: Implementation Plan (CW-35)

Spec: [design](../specs/2026-11-03-cw-35-one-release-notes-file-design.md)

## Tasks

1. Post one comment on #35 with the six options, their trade-offs, the recommendation (a separate `release-notes` branch written by the merge step) and the line that `release_notes.py` and the `merge_pr.py` check stay as they are.
2. No skill, script or role-doc change. Building the chosen option is a separate ticket.
3. Closeout (after the PR exists): as-built, spec Shipped, index rows, `docs/superpowers/release-notes/cw-35.md`.

## Verification

`python3 -I -m pytest -q agent-team/scripts` still passes. `git diff origin/main --stat` shows only files under `docs/superpowers/`.
