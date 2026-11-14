# CW-304: Show each change once in the release notes

**Status:** Shipped
**Shipped:** in PR #309, as specified
**Ticket:** [#304](https://github.com/collective-wisdom-org/collective-wisdom/issues/304)

## Goal

When a merged PR both adds a `docs/superpowers/release-notes/<id>.md` file and has a `## Release note` section in its body, `RELEASE_NOTES.md` shows that change once, from the PR body. The PR body note no longer picks up the `Context size:` line written under it.

## Today

Facts from `main` at `e6cb50b`.

- `agent-team/scripts/release_notes.py` `render(files, prs, merged)` adds one entry per note file and one per PR with a non-empty `## Release note` section, and never compares the two.
- `parse_added(log)` reads `git log --diff-filter=A --format=%x00%cI --name-only -- docs/superpowers/release-notes/` output and returns `{file name: UTC time}`. It keeps the newest add of a file and skips a commit that adds more than one note.
- `file_merge_times()` runs that git command on `origin/<target>` and returns `parse_added()`'s dict, or `{}` when git fails.
- The adding commit is the squash commit, whose subject ends with `(#N)` (for example `infra: set the builder GitHub login (CW-65) (#67)`), but the format string does not ask for the subject.
- `merge_pr.py` `publish_notes()` calls `release_notes.render(note_files(run), prs, release_notes.file_merge_times())`. `release_notes.main()` does the same with the files on disk. Neither looks inside the `merged` dict, so its value type can change.
- `section(body, heading)` returns the lines after `## <heading>` up to the next `## ` line. `open-pr` puts a `Context size: ...` line in the PR body with no heading of its own, so when it sits below the note it becomes part of the note. `merge_pr.py` also calls `section()` for the `Release note` gate and for `## Proof`.

## Design

1. **Return the PR number with the merge time.** `parse_added()` returns `{file name: Added(at, pr)}`, where `Added` is a small named tuple: `at` is the UTC time as today, `pr` is the int from a trailing `(#N)` on the commit subject, or `None` when the subject has none. `file_merge_times()` asks git for `--format=%x00%cI %s` (the time has no spaces, so the subject is everything after the first space). The newest-add and multi-add rules do not change. The `{}` on git failure does not change.
2. **Drop the file a PR note replaces.** In `render()`, collect the numbers of the PRs whose `## Release note` section is non-empty (after step 3). A note file whose `Added.pr` is in that set is skipped. Every other note file renders exactly as today: one whose commit has no `(#N)`, one added by a multi-note commit (it has no entry), one whose PR has no note, and every file when the PR list could not be read (`main()` falls back to `render(files, [], merged)`, so nothing is dropped).
3. **Cut the note at `Context size:`.** In `render()`, a PR's note text stops before the first line that starts with `Context size:`. `section()` itself does not change, so the merge gate and `## Proof` read the body as today. If the cut leaves the note empty, the PR has no note (so its file, if any, is kept).
4. **Callers.** `render()` reads `merged[name].at` where it read `merged[name]`. `publish_notes()` and `main()` need no change. A `merged` dict from an older caller is not supported; both callers are in this repo.
5. **Tests**, in `agent-team/scripts/test_release_notes.py`, table-driven per rule:
   - `parse_added`: extend the existing `LOG` fixture with subjects (one with `(#N)`, one without) and assert `Added(at, pr)` for each file.
   - One `render()` table for the dedupe rule: a PR that added `x-1.md` and has a note renders one entry (the PR one); a file with no matching PR note renders once; a PR note with no file renders once; a file whose commit has no `(#N)` renders once; a PR whose note is only a `Context size:` line keeps its file.
   - One `render()` case where a `Context size:` line follows the note and does not appear in the output.
   - Existing tests that build `merged` dicts switch to `Added` values.

## Leaves out

- fathom's own instructions and its existing note files (a GUY ticket).
- Which source is canonical for new PRs. `open-pr` keeps asking for the PR body section only.
- Matching a file to a PR by ticket ID or title when the adding commit has no `(#N)`.
- Lines other than `Context size:` that may sit under the note (for example `Closes #N`).

## Calls I made (surprising first)

- The note is cut at the first `Context size:` line, dropping that line and anything after it up to the next heading, not just that one line. Anything below that line is PR metadata, not note text.
- The cut lives in `render()`, not in `section()`, so the merge gate and the `## Proof` read in `merge_pr.py` keep their behavior.
- A PR whose note is empty after the cut counts as having no note, so its file is kept and the change still shows once.
- `parse_added()` returns a named tuple `Added(at, pr)` instead of a second dict, so the merge time and PR number come from the same commit.
- The PR number is taken only from a trailing `(#N)` on the subject, which is how GitHub writes squash commits. A `(#N)` elsewhere in the subject does not count.
- No release note file for this ticket; the PR body carries the note, as `open-pr` asks.

**Touches:** none of these (data, money, auth, user email, migrations).
