# GitHub auth for agents

A limited fine-grained PAT exported as `GITHUB_TOKEN` overrides `gh auth login` and breaks agents' PR creation.

## Symptoms

- `gh pr create` fails with `Resource not accessible by personal access token`.
- GraphQL `defaultBranchRef` fails while REST `/repos/{owner}/{repo}` works.
- `gh auth status` shows `GITHUB_TOKEN`, not `keyring`, as active.

## Correct setup

### 1. CLI: use OAuth via gh

```bash
gh auth login -h github.com -p https
gh auth status   # keyring should be active when GITHUB_TOKEN is unset
```

`<owner>/<repo>`: `project.md` § Git and GitHub. Run gh through the wrapper (`ship-loop` § Repo invariants), which clears the env vars:

```bash
~/.collective-wisdom/scripts/gh.sh pr create ...
~/.collective-wisdom/scripts/gh.sh api repos/<owner>/<repo>
```

### 2. Do not export GITHUB_TOKEN globally

Remove these from `~/.zshrc`, `~/.zprofile` and your editor's or agent app's env. `GITHUB_TOKEN` is for CI only.

```bash
export GITHUB_TOKEN=github_pat_...
export GH_TOKEN=...
```

Steps 3 to 5 (GitHub MCP, a fine-grained PAT): `github-auth-setup.md`.

## Account per repo

Each repo can use its own GitHub account. The login lives in a per-user file, not the committed `project.md`.

- **Where and what.** `~/.config/collective-wisdom/user.md`, outside the clone. GitHub logins and settings, never tokens or other secrets (keychain secret names live in `~/.config/collective-wisdom/secrets.md`, see `~/.collective-wisdom/docs/agents/secrets.md`). The shape is `~/.collective-wisdom/templates/user.md`: a Settings table (subscription figure, cap, spec and build lane limits) and a GitHub accounts table, one row per repo.
- **Who writes it.** `set up this repo` (`setup_repo.py user`), or the Chief of Staff at `start the team`, `take over` and `resume`, after the user says yes (`chief-of-staff/startup.md` § User settings check). By hand: copy the template to that path, or add a line under `## GitHub accounts`, with the backticks:

  ```
  | `github.com/acme/app` | `acme-login` |
  ```

  The first cell is the host and `owner/repo` of the `origin` remote, in any case; the second is the gh login that acts in that repo. Two rows for one repo is an error. An SSH host alias (`git@work-gh:acme/app`) gives a host gh does not know: use an https remote or the real host.
- **`gh.sh`.** With a row, `~/.collective-wisdom/scripts/gh.sh` takes that login's token (`gh auth token --user <login>`) for that one `gh` command and never runs `gh auth switch`. If the login is not signed in on that host it exits 2 and runs nothing; run `gh auth login -h <host>`. With no row it runs `gh` as before.
- **The merge gate.** `merge_pr.py` and `cos_approve_pr.py` need the row and stop without one; a merge goes ahead only when the signed-in gh login is the mapped one (or a CODEOWNERS `*` user). The gate trusts the row, so protect the file like `.git/config`.
- **gh version.** `gh auth token --user` needs a recent gh (an old one fails with `unknown flag`).

Verify with the last command in § Verify, run in each repo.

## Merge gate

The checks are in the docstrings of `~/.collective-wisdom/scripts/cos_approve_pr.py` and `~/.collective-wisdom/scripts/merge_pr.py`. Beyond them:

- **User approval.** With a Chief of Staff, a merge is approved by the user's own `approve N` reply in the Chief of Staff thread. Only when `cos_approve_pr.py` exits 0 does the Chief of Staff relay the approval to the merge child, naming that head. `merge_pr.py` merges only if the PR's head still equals the relayed one, so a push after the approval needs a new `approve N` (or a new `--auto` pass, `chief-of-staff/approvals.md` § Auto-approval). Any other head is `BLOCKED: head moved after approval`, with the conflict-resolution exception, both in `merge-pr` § Gate.
- **Hand run.** No relay, no `cos_approve_pr.py`: the user's own message in the run's thread after the `MERGE READY` it approves is the approval, and `merge_pr.py` still merges only at that report's head.
- **`--auto`.** With `Approval risk tolerance` (`project.md` § Identity) `balanced` or `permissive`, the Chief of Staff can run `~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto` instead. It runs every gate except the user's message, and also needs the approval rule to say auto for the ticket's `Risk:` level and the setting on `origin/<target>`, no renamed file, fewer than 100 files and no head carrying an unreviewed conflict-resolution note. CI, both review PASS comments (in `ci` review mode, no unresolved CI review thread instead) and the head are still checked at every setting. `--auto` and `merge_pr.py` need a gh whose `pr view --json files` returns `changeType`; with an older gh `--auto` exits 2 and the user decides.
- **No Hands.** During an active run (`chief-of-staff/no-hands.md`), `--auto` works for a ticket on the run's `started` list at any `Risk:` level: the hands path replaces the approval path and the other stops stay. A ticket the run did not start keeps the tolerance and the approval path.
- **GitHub reviews.** The team submits none (`ship-loop` § Repo invariants), and the gate needs no branch protection, ruleset or CODEOWNERS file. If those require a review, `merge_pr.py` stops and names the reviewers; GitHub does not let a PR's author approve it, so the owner's own PRs need another human's review. A codeowner (a login on the `*` line of `.github/CODEOWNERS` on `origin/<target>`) is accepted by both scripts besides the mapped login, and a PR blocked only by the missing review may merge. That relies on the ruleset's bypass list holding the repo admin role in `pull_request` mode, so GitHub itself refuses anyone else. Every other gate still runs.
- **`Require teammate approval`** (`project.md` § Git and GitHub) `on` adds a rule on top of `approve N`: an approving review on the current head from a non-author owner, member or collaborator (reviews from anyone else are ignored) and no standing changes-requested review from a teammate. `approve N` stays required either way.

## Verify

```bash
# Should succeed (wrapper clears GITHUB_TOKEN)
~/.collective-wisdom/scripts/gh.sh api graphql -f query='{ viewer { login } }'

# Should return "main", not FORBIDDEN
~/.collective-wisdom/scripts/gh.sh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { defaultBranchRef { name } } }'

# Must print the login user.md maps to this repo (the active gh account when there is no row): every agent posts as this account
~/.collective-wisdom/scripts/gh.sh api user --jq .login
```
