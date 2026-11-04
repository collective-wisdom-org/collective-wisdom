# Backfill release notes (design)

**Status:** Shipped
**Ticket:** CW-25

## Intent

CW-13 made a release note part of every PR's closeout, but the five PRs merged before it have none. `python3 scripts/release_notes.py` should show the whole history of the agent team.

## Design

- One note per past PR (#1, #2, #5, #8, #10) in `docs/superpowers/release-notes/`, in the CW-13 shape. Content comes from each PR's description.
- File names follow CW-13: `<prefix>-N.md` for a PR with a ticket (`guy-316`, `guy-330`, `cw-9`), `<YYYY-MM-DD>-<slug>.md` for one without (#1, #5).
- The date is the local merge date, 2026-11-03 for all five.
- No script or gate changes.

## Verification

`python3 scripts/release_notes.py` prints all notes with no warnings.
