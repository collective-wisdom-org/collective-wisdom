# As-built: Release notes in the PR closeout docs

**Shipped:** in PR #19
**Ticket:** CW-13 (#13)
**Spec:** [2026-11-03-release-notes-design.md](../specs/2026-11-03-release-notes-design.md)
**Plan:** [2026-11-03-release-notes.md](../plans/2026-11-03-release-notes.md)

## What shipped

- `agent-team/scripts/release_notes.py` prints every `docs/superpowers/release-notes/*.md`, newest first (date, then file name with numbers compared as numbers). A note with no dated heading prints last with a warning on stderr. With no folder or no notes it prints `No release notes yet.`
- `merge_pr.py` fetches added release notes at the head and refuses the merge with `closeout missing: no added docs/superpowers/release-notes/*.md in the PR`, or `closeout missing: release note <path> has no '# YYYY-MM-DD <title>' heading` when any added note lacks the dated heading.
- `open-pr` § Closeout docs, § Docs check and § Done when, the `merge-pr` closeout line, the shared superpowers README (new Release notes section), `documenter.md` (input and a new checklist item 5, later items renumbered), and a `Release notes listing` row in both `project.md` files.
- Tests: two rows in `test_gate` in `test_merge_pr.py`, and `test_release_notes.py` (one table-driven test).
- This PR's own note: `release-notes/cw-13.md`.

## Differs from the spec

- The heading check covers every added note, not only the first.

## Verification

- `uvx pytest -q agent-team/scripts`: 273 passed (`pytest` is not installed for `python3`).
- `shellcheck install.sh agent-team/scripts/*.sh`: clean.
- `install.sh` needed no change: `sync_dir` copies `scripts/`, skills and role docs. Apps already installed keep their old `docs/superpowers/README.md`, because the installer only seeds it when absent.
