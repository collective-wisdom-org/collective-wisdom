# CW-41 plan: Sort release notes by PR merge time

**Spec:** [2026-11-04-cw-41-release-notes-merge-order-design.md](../specs/2026-11-04-cw-41-release-notes-merge-order-design.md)

## Steps

1. `agent-team/scripts/release_notes.py`
   - Add `parse_added(log)`: pure function over `git log --diff-filter=A --format=%x00%cI --name-only` output. Returns `{file name: UTC datetime}` for paths under `docs/superpowers/release-notes/`; the newest add wins.
   - Add `file_merge_times()`: runs that git command on `refs/remotes/origin/main` from `root()`; any failure returns `{}` with no output.
   - File notes get the merge time from that map. PR notes use `mergedAt`.
   - Sort key: `(has day, day, time, kind, tiebreak)`, newest first. Timed notes use the merge day (UTC) and time. Untimed file notes keep heading date then natural file name, after timed notes of the day. Undated notes stay last.
   - Print `Merged YYYY-MM-DD HH:MM UTC.` after the heading for timed notes.
2. `agent-team/scripts/test_release_notes.py`
   - Stub `file_merge_times` in the autouse fixture (returns `{}`).
   - Replace the same-day name-order assertion with one table-driven order test (same-day files against name order, PR and file on one day, untimed fallback, git failure, `Merged` line present or absent).
   - One small `parse_added` test.
3. `agent-team/docs/superpowers/README.md` § Release notes: update the ordering sentence.
4. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
