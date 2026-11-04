# CW-41: Sort release notes by PR merge time

**Ticket:** [CW-41](https://github.com/dbeallor/collective-wisdom/issues/41)
**Status:** Draft

## Goal

`python3 scripts/release_notes.py` prints notes newest merge first and shows when each one merged. Today it sorts on the day alone, so notes from the same day come out in file name or PR number order, which says nothing about which merged first.

## Non-goals

- Changing the note format, the heading date rule, or the `merge_pr.py` closeout check.
- The one-file release notes approach (#35) and its follow-up.
- Changing where undated file notes go (still last, with the same warning).

## Where things stand

The ticket was written before PR notes existed. The script now prints two kinds of note:

- **File notes**, `docs/superpowers/release-notes/*.md`, from older PRs. They carry a heading date and no time.
- **PR notes**, the `## Release note` section of each merged PR body, read with `gh pr list`. The script already fetches `mergedAt` but keeps only its UTC date for sorting.

Both kinds need the fix.

## Design

### Merge time per note

- **PR notes:** `mergedAt` from the `gh` call already made. No new call.
- **File notes:** one git call for the whole folder:

  ```
  git log refs/remotes/origin/main --diff-filter=A --format=%x00%cI --name-only -- docs/superpowers/release-notes/
  ```

  run from `root()`. Each file's merge time is the committer date of the newest commit on `origin/main` that added it. `merge_pr.py` squash-merges, so that commit is the merge. The full ref name follows `pr_diff_delta.py`, so a tag called `origin/main` can't win.
- Times are parsed and converted to UTC.

A file note gets no merge time when git fails, there is no `.git`, there is no `origin/main`, or the file isn't on `origin/main` yet. That is not an error: no warning, and the exit code doesn't change.

### Sort order

Each note gets a key of `(day, time, kind, tiebreak)`, sorted newest first:

- A note with a merge time: day and time from the merge time in UTC.
- A file note without one: the heading date, an empty time, then the file name (natural order), as today.
- Undated file notes (no dated heading) stay last, as today, even if git knows their merge time.

Within a day, notes with a merge time come before notes without one. A copy with no git history sorts exactly as today.

The day used for a timed file note is the merge day, not the heading day. The two can differ: the heading is written at closeout, before the merge, and in local time. CW-25's note says 2026-11-03 but merged at 01:26 UTC on 2026-11-04.

### Showing the merge time

Each note with a merge time gets one line right after its heading:

```
## 2026-11-03 CW-25: Backfill release notes

Merged 2026-11-04 01:26 UTC.

`python3 scripts/release_notes.py` now also lists ...
```

Headings don't change, so file notes still print their own first line, and PR headings keep their `## <merge date> <title> (#N)` shape. A note without a merge time gets no line. An undated note with a merge time gets the line above its text.

### Docs

`agent-team/docs/superpowers/README.md` § Release notes: the sentence on ordering says newest merge first, each note shows its merge time, and file notes fall back to the heading date when git can't tell.

## Testing

One table-driven test of the order, replacing `test_print_order_and_undated_warning`'s name-order assertion. A fixture stubs the git lookup (a function returning `{file name: datetime}`) the same way `merged_prs` is stubbed. Rows:

- two same-day file notes whose merge times run against their file names, newest merge first;
- a same-day PR note and file note, ordered by time;
- a file note with no merge time, in its old heading-date position, after timed notes of its day;
- git lookup raising or returning nothing: today's order, exit 0;
- the `Merged ... UTC.` line under a timed note, and none under an untimed one.

The existing PR-merge test rows keep passing; their expected headings don't change.

The stub skips the `git log` parsing, so the parser is a pure function with one small test on sample output: newest add wins for a file added twice, offsets convert to UTC, and paths outside the folder are ignored.

## Calls I made

- **PR notes are fixed too.** The ticket only mentions file notes, but PR notes have the same same-day problem and already carry `mergedAt`, so they sort on the full time now.
- **Sort and display use the merge day, not the heading day,** for notes with a merge time. A file note can move to the next day when it merged after midnight UTC (CW-25 does).
- **Untimed notes sort after timed notes of the same day.** The realistic untimed case is a copy without git, where every note is untimed, so this rarely matters.
- **The merge time comes from `origin/main`,** by full ref name, not local `main`. A worktree's local `main` can lag; `origin/main` is what other scripts compare against.
- **Git failure is silent.** No warning and no exit code change, since a copy without `.git` is a normal install case and would warn on every run.
- **Times print in UTC,** as `Merged YYYY-MM-DD HH:MM UTC.` on its own line under the heading. Headings are unchanged.
- **Undated file notes stay last** even when git knows when they merged. The ticket didn't ask to move them.
