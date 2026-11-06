# CW-101: Cancel superseded CI runs on the same PR

**Ticket:** [CW-101](https://github.com/collective-wisdom-org/collective-wisdom/issues/101)
**Status:** Shipped
**Shipped:** in PR #153, as specified

## Goal

A new push to a PR branch cancels the CI run still going for that PR's older commit. Runs on `main` never cancel each other.

## Today

Facts from `main` at `ebc6563`, checked 2026-11-04.

- `.github/workflows/ci.yml` runs on `pull_request` and on `push` to `main`, with two jobs, `script-tests` and `shellcheck`. It has no `concurrency` block, so every push to a PR runs both jobs to the end, even after a newer push.
- The workflow lives at the repo root, not under `agent-team/`, so `install.sh` doesn't ship it. The change affects this repo only.
- `agent-team/scripts/wait-for-ci.sh` reads checks with `gh pr checks <N>`, which lists the checks on the PR's current head only. It counts a `cancel` row as a failure, but a run cancelled by a newer push sits on the old commit and never shows up there.
- `agent-team/scripts/merge_pr.py` reads `statusCheckRollup`, which is also the head commit only.
- Open tickets on the same file: #100 (one CI job) and #103 (push-to-main run). No open PR touches `.github/workflows/`.

## Change

Add one top-level block to `.github/workflows/ci.yml`, between `on:` and `jobs:`:

```yaml
# A new push to a PR cancels that PR's older run. On main each push gets its own group, so nothing is cancelled.
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.sha }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

- On `pull_request`, `github.ref` is `refs/pull/<N>/merge`: one group per PR. A newer push cancels the run in progress.
- On `push` to `main`, the key is the commit SHA, so two merges in a row land in different groups and both run.
- `cancel-in-progress` is true only for `pull_request`, so even a re-run on `main` that shares a SHA queues instead of cancelling.

No script, skill or doc changes. `wait-for-ci.sh` and `merge_pr.py` already look at the head commit only.

## Proof

CI config, so there is no unit test. The PR proves it on GitHub:

1. Push two commits to the PR branch a few seconds apart. `./scripts/gh.sh run list --branch feat/cw-101-cancel-superseded-ci` shows the older run `cancelled` and the newer one `completed` / `success`.
2. Run `./scripts/wait-for-ci.sh <N>` after that and show its last line is `pass`.
3. Merges to `main` can't be shown before merge. The PR quotes the `group` expression and names the two keys it gives on `push` (two different SHAs). After merge, the next two merges to `main` can be checked with `gh run list --branch main`.

## Leaves out

- Merging the two jobs (#100), path filters, and whether `main` runs CI on push (#103).
- Changing `wait-for-ci.sh` for a run cancelled while it was watching. That only happens if someone pushes during the wait; the ship loop already says to wait again when the head has moved past the SHA in the last line.

## Calls I made

- `cancel-in-progress` is an expression that is true only on `pull_request`, not a plain `true`. A plain `true` with a SHA key on `main` would still cancel a re-run of the same commit. Same effect as the ticket asks, one less edge.
- The PR key is `github.ref` (`refs/pull/<N>/merge`, one per PR), not `github.head_ref` (the branch name). Both work here; `github.ref` stays unique even if two forks push branches with the same name.
- The group starts with `github.workflow`, as the ticket says, so a second workflow added later won't cancel this one.
- No test file: the change is workflow config, and AGENTS.md says not to test config. Proof is the live run list on the PR.
- `wait-for-ci.sh` stays as it is (see Leaves out).
