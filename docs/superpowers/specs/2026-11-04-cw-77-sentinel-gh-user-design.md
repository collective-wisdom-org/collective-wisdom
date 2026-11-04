# CW-77: Set up the collective-wisdom-sentinel GitHub user

**Ticket:** [CW-77](https://github.com/dbeallor/collective-wisdom/issues/77)
**Status:** Shipped
**Shipped:** in PR #80, as specified

## Goal

Security review comments show `collective-wisdom-sentinel` instead of David. The repo side is one row in `docs/agents/project.md`.

## Today

Facts from `main` at `fcc78a6`, checked 2026-11-04.

- `docs/agents/project.md` § Git and GitHub: the Security reviewer login row is `none`. Chief of Staff, Builder and Code reviewer are `collective-wisdom-chief`, `collective-wisdom-builder` and `collective-wisdom-reviewer`.
- `gh auth status` lists `collective-wisdom-sentinel` in the keyring.
- `repos/dbeallor/collective-wisdom/collaborators/collective-wisdom-sentinel/permission` returns `write`, and the sentinel's own token reads `repos/dbeallor/collective-wisdom` with `.permissions.push` `true`. No account step is left.
- `merge_pr.py` runs from the root checkout and reads the reviewer logins from root `main`'s `project.md`. It counts only a `## Security review` comment written by the security reviewer login, or by the running login (`dbeallor`) while the row is `none`.
- `gh.sh` reads `project.md` from the checkout it runs in. A feature worktree posts as whatever its own branch's row says.
- No PRs are open. #70, named in the ticket, merged as `fcc78a6`.

## Change

- `docs/agents/project.md`: set the Security reviewer login row to `collective-wisdom-sentinel`. Keep the note in that cell as it is. Change nothing else.

## This PR's own security review

While this PR is open, root `main` still has the row at `none`, so the merge gate wants this PR's security review by `dbeallor`. From this branch, `AGENT_GH_ROLE=security-reviewer` posts as `collective-wisdom-sentinel`, and the gate would not count it.

So this PR's `## Security review` comment is posted with no role (as `dbeallor`), and the PR description says why. Its `## Code review` comment is posted as `code-reviewer` as usual. The Verify block shows the new row works. Every PR after this one posts its security review as the sentinel.

## Open PRs after the merge

Once this merges, the gate on root `main` wants security reviews by `collective-wisdom-sentinel`. A PR whose only PASS security review is by `dbeallor` stops passing. Such a PR must merge `main` into its branch first, so its worktree's `gh.sh` posts as the sentinel, then run the security review again on the new head and post it as `security-reviewer`.

When the PR opened, #78 (CW-56) had one; #79 (CW-53) had none. The PR description names #78. Any PR still open at merge with a `## Security review` comment by `dbeallor` needs those two steps. This PR doesn't touch other PRs.

## Verify

- Run the Verify block in `docs/agents/github-auth.md` from the worktree. `security-reviewer` prints `collective-wisdom-sentinel`, `code-reviewer` prints `collective-wisdom-reviewer`, `chief-of-staff` prints `collective-wisdom-chief`, `builder` prints `collective-wisdom-builder`, and the no-role call prints `dbeallor`.
- The sentinel's token reads `repos/dbeallor/collective-wisdom` with `.permissions.push` `true`.
- `./scripts/gh.sh pr list --state open`, then list each open PR's `## Security review` comment authors.
- Test suite (`python3 -I -m pytest -q agent-team/scripts`). The tests use fixture logins and don't read the real row, so they shouldn't change.

## Non-goals

- The account steps (invite, profile, avatar, two-factor, keyring). Those are done.
- `agent-team/templates/project.md`, the scripts, and the `cw-sentinel` suggestion in `docs/agents/personas.md`.
- Rerunning security reviews on other PRs.

## Calls I made

- This PR's security review is posted as `dbeallor`, not as the sentinel. The gate reads root `main`, where the row is still `none`, so a sentinel-posted comment would block the merge. Same call CW-75 made for the code reviewer.
- The ticket names #70 as needing a rerun, but it has merged and no PR is open now. The PR description names #78 instead, the one open PR with a `dbeallor` security review.
- No tests. A row value isn't behavior, and the Verify commands cover it.
- No plan file. The ticket changes only markdown.
