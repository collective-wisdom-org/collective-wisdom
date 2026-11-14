# CW-304 plan: show each change once in the release notes

Spec: `docs/superpowers/specs/2026-11-14-cw-304-release-notes-once-design.md`. Files: `agent-team/scripts/release_notes.py`, `agent-team/scripts/test_release_notes.py`.

## Task 1: parse the PR number with the merge time

- Add `Added = namedtuple("Added", "at pr")`. `parse_added()` returns `{name: Added(at, pr)}`; `pr` is the int from a trailing `(#N)` on the commit subject (regex `\(#(\d+)\)\s*$`), else `None`. Newest add wins and multi-note commits are skipped, as today.
- `file_merge_times()` uses `--format=%x00%cI %s`; the first line of each commit is `<time> <subject>`.
- Update the `LOG` fixture and `test_parse_added...` to include subjects and assert `Added`.

## Task 2: render dedupe and Context size cut

- In `render()`, cut each PR note at the first line starting `Context size:`; an empty result means no note.
- Collect the numbers of PRs that have a note; skip a file whose `merged[name].pr` is in that set. Read `merged[name].at` where the code used `merged[name]`.
- Tests: one table-driven `render()` test for the dedupe rule (file+PR note once; file only once; PR note only once; file with `pr=None` once; PR with only a Context size line keeps its file) and a case where a Context size line is absent from output. Switch existing tests' `merged` values to `Added`.

## Verify

`python3 -I -m pytest -q agent-team/scripts` (or `uvx pytest -q agent-team/scripts`), then `python3 agent-team/scripts/release_notes.py | head -30` for a sanity check.
