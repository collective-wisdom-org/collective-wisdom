# CW-65: Set up the collective-wisdom-builder GitHub user

**Ticket:** [CW-65](https://github.com/dbeallor/collective-wisdom/issues/65)
**Status:** Draft

## Goal

Ship-loop PRs, notes and ticket moves show `collective-wisdom-builder` instead of David. The repo side is one row in `docs/agents/project.md`.

## Today

Facts from `main` at `4be5d07`, checked 2026-11-04.

- `docs/agents/project.md` § Git and GitHub: the Builder login row is `none`, and Chief of Staff is `collective-wisdom-chief`.
- `gh auth status` lists `collective-wisdom-builder` in the keyring. `dbeallor` is the active account.
- `AGENT_GH_ROLE=chief-of-staff ./scripts/gh.sh api user --jq .login` prints `collective-wisdom-chief`. The builder role and the no-role call print `dbeallor`.
- **`collective-wisdom-builder` has no access to the repo yet.** The repo is private, the account isn't in the collaborator list, and it has no pending invite. Its token gets `404 Not Found` on `repos/dbeallor/collective-wisdom`.
- There are no open PRs, and PR #64 (CW-51) has merged. No `Head moved to` note needs reposting.

## Change

- `docs/agents/project.md`: set the Builder login row to `collective-wisdom-builder`. Keep the note in that cell as it is. Change nothing else.

`gh.sh` reads `project.md` from the checkout it runs in. Once this row is on the branch, every `AGENT_GH_ROLE=builder` call from this worktree runs as the new account. Until the collaborator invite is accepted, those calls fail with 404.

## Order

1. David invites `collective-wisdom-builder` as a collaborator with write access and accepts the invite while signed in as that account. The profile and two-factor sign-in, also from the ticket, can happen any time before merge.
2. The build checks access: the builder's token reads `repos/dbeallor/collective-wisdom` and `.permissions.push` is `true`. If it doesn't, the build stops with `BLOCKED:` before it opens the PR.
3. Commit the row change and open the PR with `AGENT_GH_ROLE=builder`. The PR author is the new account, which proves the setup works end to end.

## Verify

- Run the Verify block in `docs/agents/github-auth.md` from the worktree. `builder` prints `collective-wisdom-builder`, `chief-of-staff` prints `collective-wisdom-chief`, and the no-role call prints `dbeallor`. `code-reviewer` and `security-reviewer` print `dbeallor`, because their rows stay `none`.
- `./scripts/gh.sh pr list --state open`, then check each open PR for `Head moved to` notes. Today there are none, so this step is expected to find nothing. Any note found that was posted by `dbeallor` gets a fresh copy posted as the builder.
- Test suite (`python3 -I -m pytest -q agent-team/scripts`). The tests use `cw-builder` fixtures and don't read the real row, so they shouldn't change.

## Non-goals

- The account steps themselves (invite, profile, two-factor, keyring). David does these.
- The Code reviewer and Security reviewer rows. They stay `none`.
- `agent-team/templates/project.md` and the scripts.

## Calls I made

- The build waits for repo access before it pushes the row change, instead of opening the PR as `dbeallor`. Opening it as the builder tests the change. The other order would leave every builder call on this branch failing anyway.
- No tests. A row value isn't behavior, and the Verify commands cover it.
