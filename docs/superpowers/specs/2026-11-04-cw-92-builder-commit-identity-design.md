# CW-92: Author and push ticket branch commits as the builder user

**Ticket:** [CW-92](https://github.com/dbeallor/collective-wisdom/issues/92)
**Status:** Draft

## Goal

In team mode, every commit on a `feat/cw-N-*` branch is authored, committed and pushed as the builder user, so a PR's commits, its author and the squash commit on `main` show one identity. Merges and the owner's hand commits stay on the owner's account.

## Today

Facts from `main` at `57e7470`, checked 2026-11-04.

- `agent-team/scripts/gh.sh` swaps in a role's token as `GH_TOKEN` for one `gh` call when `AGENT_GH_ROLE` is set. Nothing does the same for `git`.
- `agent-team/docs/agents/github-auth.md` line 113: "Commits and pushes keep your own git config and gh credential."
- `ship-loop` § Team mode, **GitHub users**, covers only `gh.sh` calls. The child commits and pushes with the machine's git identity, so PR #85's commits are authored by `david_beallor@Davids-MacBook-Pro-2.local`, which GitHub links to no account.
- `AGENT_GH_ROLE=builder ./scripts/gh.sh api user` returns login `collective-wisdom-builder`, id `352275848`, name `Builder - Collective Wisdom`.
- The `origin` remote is `https://github.com/dbeallor/collective-wisdom.git`. `install.sh` syncs the whole `scripts/` directory, so a new script there ships to apps with no installer change.

## Change

### New `agent-team/scripts/git.sh`

A wrapper for `git`, shaped like `gh.sh`, run as `AGENT_GH_ROLE=builder ./scripts/git.sh <git args>`.

- Role unset, or a role whose `project.md` login is `none`: `exec git "$@"`. Today's behaviour.
- Unknown role or bad `project.md` row: exit 2 with one `git.sh:` line on stderr, as `gh.sh` does.
- A role with a login:
  1. Get the token with `gh auth token -u <login>` (with `GITHUB_TOKEN` and `GH_TOKEN` cleared). No token: exit 2 with `git.sh: no gh login for <login>; ...` and run no git command. It never falls back to the owner.
  2. Read the account's `id` and `name` with that token (`gh api user`). Identity: name is the profile name, or the login if the name is empty; email is `<id>+<login>@users.noreply.github.com`, the address GitHub links to the account.
  3. Export `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL` for this one git process, so `commit`, `merge`, `rebase` and `cherry-pick` all write the builder.
  4. Pass the credential through the environment and two `-c` options on the command line: `-c credential.helper=` (clears the keychain and other helpers for this call) and `-c 'credential.helper=!f() { test "$1" = get && echo username=x-access-token && echo "password=$GIT_SH_TOKEN"; }; f'`. The token lives only in `GIT_SH_TOKEN` in that process. It is never written to git config, a file, the remote URL or the keychain (the helper ignores `store`).
  5. For `push`: if the push URL isn't https, exit 2. Then, check every commit not yet on `origin` (`git rev-list HEAD --not --remotes=origin`) has the builder's author email. If one doesn't, exit 2, name the commit, and push nothing. The message gives the fix: `AGENT_GH_ROLE=builder ./scripts/git.sh rebase -r <base> --exec 'git commit --amend --no-edit --reset-author'`.
  6. `exec git -c ... "$@"`.

### `agent-team/.claude/skills/ship-loop/SKILL.md` § Team mode

One sentence added to **GitHub users**: run every git command that writes commits or pushes on the ticket branch (`commit`, `merge`, `rebase`, `push`, `cherry-pick`) as `AGENT_GH_ROLE=builder ./scripts/git.sh <args>`, the child's subagents included. The `none` and exit 2 rules already in that bullet apply to it. **Spec stage** and **Build stage** are not edited; their "commit and push" now goes through that rule.

### `agent-team/docs/agents/github-auth.md` § Agent users

- Replace the line 113 sentence with: the builder's commits and pushes on a ticket branch go through `scripts/git.sh`, which authors them with the builder's noreply address and pushes with its keyring token; a `none` row keeps your git config and credential; commits you make by hand keep your own git config.
- § Set up: new step telling the owner to set `git config --global user.email` to an address on their own GitHub account (a verified email or their noreply address), so their hand commits link to them.
- § Verify: one command, `AGENT_GH_ROLE=builder ./scripts/git.sh var GIT_AUTHOR_IDENT`, which prints the builder's name and noreply email.

### Tests: `agent-team/scripts/test_git_sh.py`

One table-driven test, same fake-`gh` pattern as `test_gh_sh.py`, against a temp repo with a local bare remote:

- no role and `none` row: commit uses the repo's own `user.email`;
- builder row: commit author and committer are `<id>+cw-builder@users.noreply.github.com`;
- login missing from the fake keyring: exit 2, one stderr line, no commit made;
- push with a commit by another author: exit 2, remote ref unchanged;
- after a builder push, `git config --list` and `.git/config` hold no token.

Plus one check that `git.sh credential fill` for `https://github.com` returns the fake token, so the helper wiring is exercised without a network push.

## Acceptance

From the ticket:

- A ship-loop PR opened after this merges shows the builder as author of every branch commit, linked to `collective-wisdom-builder`; `./scripts/gh.sh api repos/<owner>/<repo>/commits/<sha> --jq .author.login` prints it.
- `Builder login` `none`: the machine's identity and credential, as before.
- Builder login missing from the keyring: one error line, nothing pushed.
- No token in `git config --list`, `.git/config` or the remote URL after a push.
- `merge_pr.py` still merges as the owner (unchanged).

## Non-goals

- Rewriting commits on `main` or open branches.
- Stopping agent accounts from merging in the web UI.
- Commit identities for the reviewer and Chief of Staff roles.
- `merge_pr.py`, `gh.sh`, `kickoff-feature`, `build-from-plan`, `chief-of-staff`.
- Pushing as the builder over an SSH remote (see Calls I made).

## Calls I made

- **Push refuses commits by anyone but the builder.** The ticket asks that every branch commit show the builder; a forgotten wrapper would quietly break that, so the push stops and prints the rebase command that fixes it. Only commits not yet on `origin` are checked, so merging `main` in doesn't trip it.
- **A new `scripts/git.sh` wrapper, not git config.** Setting `user.email` in the worktree's config would also need a credential in config or a file, which the ticket forbids. Per-command environment matches how `gh.sh` works.
- **Email is the GitHub noreply address `<id>+<login>@users.noreply.github.com`,** looked up live through the builder's token. No new `project.md` row and nothing to keep in sync.
- **Author name is the GitHub profile name** (`Builder - Collective Wisdom`), falling back to the login.
- **SSH remotes are not handled.** With an `ssh://` or `git@` push URL the helper never runs and git would push with the machine's SSH key. `git.sh` exits 2 on push in that case instead of guessing an https URL. This repo uses https.
- **This PR's own spec commit is authored by the machine identity,** because `git.sh` doesn't exist yet. Build commits after `git.sh` lands on the branch go through it, so the commits on this PR will be mixed. The push check looks only at commits not yet on `origin`, and the spec commit is already pushed, so it doesn't block this branch. I won't rewrite the spec commit.
- **The build writes a plan,** since the ticket adds a script and isn't markdown only.
