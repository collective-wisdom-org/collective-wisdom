# Release notes in the PR closeout docs: Implementation Plan (CW-13)

Spec: [design](../specs/2026-11-03-release-notes-design.md)

## Tasks

1. `agent-team/scripts/release_notes.py`: print all `docs/superpowers/release-notes/*.md`, newest first (date desc, then file name with numbers compared numerically, desc); undated files last with stderr warning; empty/missing folder prints `No release notes yet.`. Root found with `Path(__file__).absolute().parent.parent`, like `docs_index.py`.
2. `agent-team/scripts/test_release_notes.py`: one table-driven test (ordering, undated last plus warning, missing folder).
3. `agent-team/scripts/merge_pr.py`: add `RELEASE` path regex; `read_facts` fetches added release-note content at head; `gate` returns `closeout missing: no added docs/superpowers/release-notes/*.md in the PR` or `closeout missing: release note <path> has no '# YYYY-MM-DD <title>' heading`, placed after the index checks.
4. `agent-team/scripts/test_merge_pr.py`: green fixture gains a release note; two rows in the `test_gate` table.
5. Docs: `open-pr` § Closeout docs / Docs check / Done when; `merge-pr` closeout line; `agent-team/docs/superpowers/README.md` Release notes section; `agent-team/docs/agents/documenter.md` inputs and checklist; `agent-team/templates/project.md` and `docs/agents/project.md` `Release notes listing` row.
6. Closeout (after the PR exists): as-built, spec Shipped, index rows, `docs/superpowers/release-notes/cw-13.md`.

## Verification

`python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh agent-team/scripts/*.sh`; run `python3 scripts/release_notes.py`; `./install.sh --dry-run` into a scratch repo.
