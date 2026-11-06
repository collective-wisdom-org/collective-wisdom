# CW-100: shellcheck and pytest in one CI job

**Status:** Shipped
**Shipped:** in PR #155, as specified
**Ticket:** [#100](https://github.com/collective-wisdom-org/collective-wisdom/issues/100)

## Goal

Each CI run bills one job minute for shellcheck and pytest instead of two. GitHub rounds every job up to a full minute, and the two jobs together do about 40 seconds of work.

## Today

- `.github/workflows/ci.yml` has three jobs: `script-tests` (scope step, setup-python, pip install pytest, pytest), `shellcheck` (the same scope step, then shellcheck) and `mod-tests` (Node, not required).
- Both `script-tests` and `shellcheck` run the same `ci scope` step (`review_scope.py --ci`) and each uses one of its two outputs.
- `docs/agents/project.md` § Commands lists `script-tests` and `shellcheck` as the required CI checks.
- Branch protection does not name them. `main` has no classic branch protection, and its two rulesets ("Require PR to Merge to Main" and "Required Approved PR by Codeowners to Merge to Main") have an empty `required_status_checks` list. I read this from the API on 2026-11-05. The ticket assumes both checks are required by name; they are not.
- `scripts/merge_pr.py` and `scripts/wait-for-ci.sh` never look a check up by name. `merge_pr.py` requires every check in the PR's status rollup to have passed, and `wait-for-ci.sh` watches `gh pr checks`. `project_config.py` reads the `Required CI checks` row only to tell `none (no CI yet)` from anything else.

## Builds

- `ci.yml`: one job named `checks` replaces `script-tests` and `shellcheck`. Its steps, in order: checkout (depth 2), `ci scope` (unchanged, run once), `shellcheck` when `shellcheck=run`, then setup-python, pip install pytest and `pytest` when `tests=run`. Each step keeps its own name in the Actions log, so a failure says which one broke.
- Pytest runs even when shellcheck fails (`if: ${{ !cancelled() && steps.scope.outputs.tests == 'run' }}`), so one run reports both kinds of failure.
- `mod-tests` stays its own job, unchanged.
- `docs/agents/project.md`: the `Required CI checks` row says `checks`.
- No script or test changes. Nothing reads the old job names.

## Your step: required check in the ruleset

No agent changes repo settings, so this part of the ticket is yours. Since no ruleset requires `script-tests` or `shellcheck` today, there is nothing to rename and nothing that blocks this PR from merging.

- **After this PR merges**, if you want CI enforced on `main`: in Settings → Rules → "Require PR to Merge to Main", add the status check `checks` (source GitHub Actions). Do it after the merge, not before. Before the merge, `checks` doesn't exist on `main`, and other open PRs whose branches predate it would wait forever for a check that never reports until they merge `main` in.
- If you skip it, nothing breaks. `merge_pr.py` already refuses a PR with any failed or unfinished check.
- If you had added `script-tests` or `shellcheck` as required checks before this merges, remove them first, before the merge: once this PR is in, no run reports those names and every PR would wait on them.

## Acceptance

- A run shows one `checks` job (plus `mod-tests`), with `shellcheck` and `pytest` as separate steps.
- This PR's own CI is the green case: it changes `ci.yml`, so the scope step says shellcheck runs, and it changes a non-docs file, so pytest runs.
- The red cases are checked on throwaway commits on this branch, reverted before review: one with a shellcheck error in a script, one with a failing assertion. Each must turn `checks` red with the right step marked failed. The PR's Proof section links both runs.
- `wait-for-ci.sh` exits 0 on the green head, and `merge_pr.py` merges it at merge time.

## Leaves out

- Folding `mod-tests` into the same job. It bills its own minute too, but the ticket scopes two jobs, and `mod-tests` is not a required check.
- Cancelling superseded runs, path filters and the push-to-main run (separate tickets).
- Any change to `review_scope.py --ci` or its output line.

## Calls I made (surprising first)

- **Branch protection names neither check today**, so the ticket's rename step is really "add `checks` as a required check after merge, if you want one". The spec says so instead of planning a rename.
- **The job is named `checks`.** Short, and it covers both linting and tests. The ticket left the name open.
- **Pytest still runs after a shellcheck failure**, so one run reports both. The ticket asks only that a failure names the step that broke.
- **Shellcheck runs first**, as the ticket says. It is the faster step and needs no setup.
- **The red-case proof uses reverted throwaway commits on this PR's branch**, not separate PRs. The acceptance asks for "a PR with a shellcheck error and a PR with a failing test"; two extra PRs would cost two more tickets' worth of noise for the same signal.
- **This spec edits `docs/agents/project.md`**, which is on the auto-approval path. With `Approval risk tolerance` `strict` nothing is auto-approved anyway, so the spec and merge both wait for you.

## Touches

None of these (data, money, auth, user email, migrations). CI config and one row in `project.md`.
