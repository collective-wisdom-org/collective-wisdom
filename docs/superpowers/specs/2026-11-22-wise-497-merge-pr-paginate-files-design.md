# WISE-497: Read the PR file list from the paginated API in merge_pr.py

**Status:** Draft
**Ticket:** [#497](https://github.com/collective-wisdom-org/collective-wisdom/issues/497)

## Goal

`merge_pr.py` sees every file in the PR, so a PR of more than 100 files passes the closeout check when its spec says Shipped. Today it refuses PR #496 (WISE-488, 129 files) because the spec is past the 100th file.

## Today

- `agent-team/scripts/merge_pr.py` asks for `files` in `FIELDS`, and `read_facts` reads them with one `gh pr view --json`. GitHub returns at most 100 files there.
- Two checks read `f["files"]`: the spec fetch in `read_facts` (specs under `docs/superpowers/specs/` that are not `DELETED`) and the closeout check in `gate` (an added `docs/superpowers/as-built/*.md`). Both run only on an open PR; `gate` returns before the closeout check for a merged or closed one.
- `cos_brief.py` reads files twice, both capped at 100 and silent about it: `migrations_line` (`gh pr list --json number,files` for the migration clash check) and `cmd_pr` (`gh pr view --json ...files...` for the `files: N` line).
- `cos_approve_pr.py` adds `files` to its own `gh pr view` and stops with "PR has N or more files, too many to check" at `FILES_CAP = 100`. That fails closed: no auto-approval, never a wrong pass.

## Change

1. `merge_pr.py`:
   - Drop `files` from `FIELDS`.
   - New `pr_files(pr, run)`: runs `gh.sh api repos/{owner}/{repo}/pulls/<N>/files --paginate --jq '.[] | {path: .filename, status}'`, reads one JSON object per line, and returns `[{"path": ..., "changeType": ...}]`. `status` maps `added` to `ADDED`, `removed` to `DELETED`, `renamed` to `RENAMED`, anything else (`modified`, `changed`, `copied`, `unchanged`) to `MODIFIED`. A failed read raises `CmdError` like every other read, so the merge stops with exit 2.
   - `read_facts` sets `f["files"] = pr_files(pr, run)` when the PR is open, and `[]` otherwise. Every file-list check reads the full list from there; the checks themselves don't change.
2. `cos_brief.py`: state the cap instead of paginating, since both reads only inform the brief.
   - `cmd_pr`: when the PR has 100 files, the line reads `files: 100+ (...)` (counts by area cover the first 100).
   - `migrations_line`: another open PR that comes back with 100 files is named in the line as `#N has 100+ files, not checked`, so a missed clash is visible.
3. `cos_approve_pr.py`: unchanged. Sharing the helper would mean importing `merge_pr.py` or adding a module for a check that already fails closed. The PR lists it as left on purpose.
4. Test in `test_merge_pr.py`, table-driven, through `read_facts` and `gate` with a fake runner that serves the paginated `pulls/<N>/files` read as two pages (100 + 29 lines):
   - 129 files, the Shipped spec at position 120 and the added as-built past 100: closeout passes.
   - 129 files with no spec: fails with "no spec in the PR has **Status:** Shipped".
   - The status mapping (`removed` spec is not fetched; `added` as-built counts, `modified` doesn't) rides in the same table.
   The existing `fake` runner moves its file list from the `pr view` JSON to the new `api .../files` read.

## Proof

- `python3 -I -m pytest -q agent-team/scripts` passes, including the new table.
- A read-only call of `merge_pr.pr_files("496", merge_pr.run)` from a Python prompt in this worktree (no gate, no merge; `merge_pr.py` has no dry-run mode) returns all 129 files, with the WISE-488 spec among them.
- `/usr/bin/grep -nE 'files' agent-team/scripts/*.py` shows no `--json ... files` read without pagination or a cap note, except `cos_approve_pr.py`, which the PR lists.

## Leaves out

- Raising the 100-file limit anywhere else, or changing which files count as the hands path.
- `cos_approve_pr.py`'s `FILES_CAP` stop.
- The REST endpoint's own limit of 3000 files per PR. A PR that big is out of reach for this team anyway.

## Calls I made

- `cos_brief.py` gets cap notes, not pagination: the ticket says pick the smaller change, and paginating the clash check would mean one more API call per open PR on every brief.
- `merge_pr.py` reads the file list only for an open PR. A merged or closed PR never reaches a file check, so it skips the call.
- Pagination uses `--paginate --jq` with one object per line rather than `--slurp`, so it works on any `gh` that has `--paginate`.
- `cos_approve_pr.py` is left as is (fails closed) rather than sharing the helper.
- This PR touches `merge_pr.py`, which is on the hands path, so the merge waits for the user's approval.
