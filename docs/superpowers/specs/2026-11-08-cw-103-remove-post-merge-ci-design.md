# CW-103: Remove the post-merge CI run on main

**Status:** Shipped
**Shipped:** in PR #193, as specified
**Ticket:** [#103](https://github.com/collective-wisdom-org/collective-wisdom/issues/103)

## Goal

Every squash merge runs CI again on `main`, on a tree its PR already tested. That is about 15 percent of runs (18 of the last 100). The user decided on 2026-11-08 to drop that run. CI runs on pull requests only, and the docs say so, including that nothing tells the team when `main` goes red.

## Today

Facts from `main` at `2b797f0`.

- `.github/workflows/ci.yml` triggers on `pull_request` and on `push` to `main`.
- Its `concurrency` block exists partly for `push`: the group falls back to `github.sha` for non-PR events, `cancel-in-progress` is true only for `pull_request`, and the comment says "On main each push gets its own group, so nothing is cancelled."
- The `ci scope` step passes `EVENT` and runs `review_scope.py --ci` only when it is `pull_request`; any other event runs both steps. Its comment lists "push" among the unsure cases. The checkout comment says "on a pull_request the checkout is GitHub's merge commit".
- `merge_pr.py` merges after the PR head is green. Branch protection on `main` does not require the branch to be up to date, so a merged tree can differ from the tested one when another PR merged first. The post-merge run was the only check of that tree.
- `README.md` § Propose changes says "CI does the same" about the tests. `docs/agents/project.md` § Commands lists `Required CI checks` as `checks`. Neither says when CI runs.
- No script or test reads the workflow's triggers. `test_review_scope.py` only uses the path `.github/workflows/ci.yml` as a diff entry, and `test_approval_policy.py` lists it as an approval-path file.

## Builds

1. **Trigger.** `ci.yml` keeps `on: pull_request:` and drops the `push` trigger.
2. **Concurrency.** The group becomes `${{ github.workflow }}-${{ github.ref }}` and `cancel-in-progress: true`. The comment says a new push to a PR cancels that PR's older run, and nothing about `main`.
3. **CI scope step.** The `EVENT` env and its `if` go; the step always runs `review_scope.py --ci HEAD^1 HEAD` and keeps the run-both fallback for a script error or a missing `ci-scope:` line. The comment drops "push". The checkout comment drops "on a pull_request".
4. **README.** `README.md` § Propose changes gets two sentences after the CI test line: CI runs on pull requests only, so `main` is tested only through its PRs, and a merge can still leave `main` red when another PR merged first; nothing today tells the team when that happens.
5. **project.md.** The `Required CI checks` row's note says the same in short: CI runs on pull requests only, main is tested only through PRs, and nothing today reports a red main. No new backticks in the cell, so scripts still read `checks`.

## Leaves out

- Any change to the `pull_request` trigger, the jobs or their steps beyond the lines above.
- A replacement alert, scheduled run or merge-queue for `main` (ticket out of scope).
- Branch protection settings.
- Tests. The change is workflow config and prose; no script reads the triggers.
- Old specs and plans that mention the `main` run.

## Calls I made

- The README sentence also names why `main` can go red (a PR merged after another one, without being re-tested). The ticket asks only for "nothing today tells the team"; without the reason the note reads as if `main` can't break.
- `cancel-in-progress` becomes plain `true` rather than keeping the `pull_request` check, since every run is now a PR run.
- The `ci scope` step keeps its run-both default for a script error, even though the event check goes.
- The `project.md` note goes in the `Required CI checks` row's cell, not a new row or a paragraph under the table.
- Both changed files (`ci.yml`, `docs/agents/project.md`) are on the approval path. The repo's tolerance is `strict`, so this spec waits for the user either way.
