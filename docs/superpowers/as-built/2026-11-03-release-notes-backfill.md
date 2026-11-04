# As-built: Backfill release notes

**Shipped:** in PR #24
**Ticket:** CW-25 (#25)
**Spec:** [2026-11-03-release-notes-backfill-design.md](../specs/2026-11-03-release-notes-backfill-design.md)

## What shipped

- Release notes for #1 (`2026-11-03-publish-agent-team.md`), #2 (`guy-316.md`), #5 (`2026-11-03-tracker-choice.md`), #8 (`guy-330.md`) and #10 (`cw-9.md`).
- This PR's own note, `cw-25.md`.

## Differs from the spec

Nothing.

## Verification

`python3 scripts/release_notes.py` prints all seven notes with no warnings on stderr. No code changed, so no tests were added.
