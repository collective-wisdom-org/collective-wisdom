# As-built: Lighten the closeout docs per ticket

**Shipped:** in PR #66
**Ticket:** CW-55 (#55)
**Spec:** [2026-11-04-cw-55-lighten-closeout-docs-design.md](../specs/2026-11-04-cw-55-lighten-closeout-docs-design.md)

## Differs from the spec

- This PR still ships the old-shape closeout: this as-built file, `index/cw-55.md` and `release-notes/cw-55.md`. The `merge_pr.py` on root `main` is the old gate until this PR merges, and it refuses a PR without them. The other index files are deleted as specified; a follow-up deletes `index/cw-55.md` and the `index/` folder.
- `release_notes.py` prints its docstring and exits 0 when given any argument (`--help`), because `test_script_runs_by_link_path` runs every script with `--help` and the script would otherwise call `gh`.
- On the same date, PR notes sort before file notes. The spec did not say how to mix them.
- `merge_pr.py` uses `release_notes.section` for the `## Release note` parser instead of a second copy.
- The test for `release_notes.py` stubs the merged-PR read for the whole file, so the existing order test keeps its body unchanged.
