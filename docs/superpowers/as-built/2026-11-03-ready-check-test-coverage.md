# As-built: Cover the live gh path and symlinked root of cos_ready_check

**Shipped:** in PR #18
**Ticket:** none
**Spec:** [2026-11-03-ready-check-test-coverage-design.md](../specs/2026-11-03-ready-check-test-coverage-design.md)

## What shipped

- `agent-team/scripts/test_cos_ready_check.py`: `test_live_gh_call`, one table-driven test of the real `gh` path with `subprocess.run` stubbed. Rows: a failed `gh` call exits 2, paginated output (several arrays back to back, two branches at different shas) reports `pushed` for the ticket's own branch, empty refs report `writing`. Every row also checks the `gh api --paginate .../matching-refs/heads/<prefix>` command that was built.
- `agent-team/scripts/test_symlinked_root.py`: one `cos_ready_check` row.

## Differs from the spec

Nothing.

## Verification

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass. No script or skill text changed.
