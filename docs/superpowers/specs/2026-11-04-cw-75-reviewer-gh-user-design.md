# CW-75: Set up the collective-wisdom-reviewer GitHub user

**Ticket:** [CW-75](https://github.com/dbeallor/collective-wisdom/issues/75)
**Status:** Draft

## Goal

Code review comments show `collective-wisdom-reviewer` instead of David. The repo side is one row in `docs/agents/project.md`.

## Today

Facts from `main` at `6abe6d4`, checked 2026-11-04.

- `docs/agents/project.md` § Git and GitHub: the Code reviewer and Security reviewer login rows are `none`. Chief of Staff is `collective-wisdom-chief` and Builder is `collective-wisdom-builder`.
- `gh auth status` lists `collective-wisdom-reviewer` in the keyring. Its token reads `repos/dbeallor/collective-wisdom` with `.permissions.push` `true`, so no invite step is left.
- `AGENT_GH_ROLE=code-reviewer ./scripts/gh.sh api user --jq .login` prints `dbeallor`.
- `merge_pr.py` runs from the root checkout and reads the reviewer logins from root `main`'s `project.md`. It counts only a `## Code review` comment written by the code reviewer login, or by the running login (`dbeallor`) while the row is `none`.
- `gh.sh` reads `project.md` from the checkout it runs in. A feature worktree posts as whatever its own branch's row says.
- Open PRs #70 (CW-59), #73 (CW-23) and #74 (CW-68) each have `## Code review` comments, all by `dbeallor`.

## Change

- `docs/agents/project.md`: set the Code reviewer login row to `collective-wisdom-reviewer`. Keep the note in that cell as it is. Change nothing else.

## This PR's own code review

While this PR is open, root `main` still has the row at `none`, so the merge gate wants this PR's code review by `dbeallor`. From this branch, `AGENT_GH_ROLE=code-reviewer` posts as `collective-wisdom-reviewer`, and the gate would not count it.

So this PR's `## Code review` comment is posted with no role (as `dbeallor`), and the PR description says why. The Verify block shows the new row works. Every PR after this one posts as the reviewer.

## Open PRs after the merge

Once this merges, the gate on root `main` wants code reviews by `collective-wisdom-reviewer`. A PR whose only PASS review is by `dbeallor` stops passing. Each such PR needs two steps, in order:

1. Merge `main` into its branch, so its worktree's `gh.sh` posts as the reviewer.
2. Run the code review again on the new head and post it as `code-reviewer`.

Step 1 moves the head, so the `Head moved to` note path doesn't apply: the old review is by the wrong login. The PR description names every open PR that still has a `dbeallor` code review when this PR opens. Today that is #70, #73 and #74. A PR that merges before this one is fine as it is.

This PR doesn't touch those PRs. Their own children rerun the review when the Chief of Staff tells them to.

## Verify

- Run the Verify block in `docs/agents/github-auth.md` from the worktree. `code-reviewer` prints `collective-wisdom-reviewer`, `chief-of-staff` prints `collective-wisdom-chief`, `builder` prints `collective-wisdom-builder`, and `security-reviewer` and the no-role call print `dbeallor`.
- The reviewer's token reads `repos/dbeallor/collective-wisdom` with `.permissions.push` `true`.
- `./scripts/gh.sh pr list --state open`, then list each open PR's `## Code review` comment authors.
- Test suite (`python3 -I -m pytest -q agent-team/scripts`). The tests use fixture logins and don't read the real row, so they shouldn't change.

## Non-goals

- The Security reviewer row. It stays `none` until that account exists.
- The account steps (invite, profile, two-factor, keyring). Those are done.
- `agent-team/templates/project.md` and the scripts.
- Rerunning the reviews on #70, #73 and #74.

## Calls I made

- This PR's code review is posted as `dbeallor`, not as the reviewer. The gate reads root `main`, where the row is still `none`, so a reviewer-posted comment would block the merge. Changing the gate to read the PR's row would let any PR pick its own reviewer, which the gate's comment says it must not do.
- The open PRs need `main` merged in before their review is rerun, or the rerun posts as `dbeallor` again. The PR description says so next to the PR list.
- No tests. A row value isn't behavior, and the Verify commands cover it.
- No plan file. The ticket changes only markdown.
