# Cover the live gh path and symlinked root of cos_ready_check (design)

**Status:** Shipped
**Ticket:** none (PR #18)

## Intent

CW-11 shipped `cos_ready_check.py` with tests that read fixture files, so the path that calls the real `gh` never runs under test. The script is also missing from the symlinked-root check that covers the other `cos_*` check scripts. A break in either would stop the Chief of Staff's ready check without anyone noticing.

## Design

- `test_cos_ready_check.py`: one table-driven test, `test_live_gh_call`, stubs `subprocess.run` and covers a failed `gh` call (exit 2), `gh api --paginate` output that arrives as several arrays back to back (reports `pushed` for the right branch), and an empty ref list (`writing`).
- `test_symlinked_root.py`: one row so `cos_ready_check` runs under the symlinked-root check.
- No script, skill or doc changes.

## Verification

`python3 -I -m pytest -q agent-team/scripts` passes and `shellcheck install.sh agent-team/scripts/*.sh` is clean.
