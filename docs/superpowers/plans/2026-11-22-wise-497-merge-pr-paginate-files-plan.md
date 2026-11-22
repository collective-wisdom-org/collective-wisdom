# WISE-497 plan: paginated PR file list in merge_pr.py

Spec: [design](../specs/2026-11-22-wise-497-merge-pr-paginate-files-design.md). Test command: `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: merge_pr.py and its test

- Drop `files` from `FIELDS`; add `pr_files(pr, run)` (`gh.sh api repos/{owner}/{repo}/pulls/<N>/files --paginate --jq '.[] | {path: .filename, status}'`, one JSON object per line, status mapped to `changeType`); `read_facts` sets `f["files"]` from it for an open PR, `[]` otherwise.
- `test_merge_pr.py`: move the `fake` runner's file list to the new api read; add one table-driven test (129 files over two pages; Shipped spec at 120 passes, no spec fails, removed/added/modified mapping).

## Task 2: cos_brief.py cap notes

- `cmd_pr`: `files: 100+ (...)` when 100 files come back. `migrations_line`: name each other open PR with 100 files as `#N has 100+ files, not checked`. Add a small case to the existing cos_brief test only if it fits an existing table.

## Task 3: verify

- Full test suite; `/usr/bin/grep -nE 'files' agent-team/scripts/*.py` for leftover `--json ... files` reads (only `cos_approve_pr.py` stays, listed in the PR).
