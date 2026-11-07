# GitHub auth for agents

Agents and local scripts need GitHub API access for PRs, issues and the GitHub MCP server. A recurring failure is a **limited fine-grained PAT** exported as `GITHUB_TOKEN`, which overrides `gh auth login` and breaks PR creation.

## Symptoms

- `gh pr create` fails with `Resource not accessible by personal access token`
- GraphQL queries for `defaultBranchRef` fail while REST `/repos/{owner}/{repo}` works
- `gh auth status` shows **GITHUB_TOKEN** as the active account instead of **keyring**

## Correct setup

### 1. CLI — use OAuth via gh

```bash
gh auth login -h github.com -p https
gh auth status   # keyring should be active when GITHUB_TOKEN is unset
```

`<owner>/<repo>` is the repo in the app's `docs/agents/project.md` § Git and GitHub. Run gh through the repo wrapper (`ship-loop` § Repo invariants), which clears the env vars:

```bash
~/.collective-wisdom/scripts/gh.sh pr create ...
~/.collective-wisdom/scripts/gh.sh api repos/<owner>/<repo>
```

### 2. Do not export GITHUB_TOKEN globally

Remove these from `~/.zshrc`, `~/.zprofile` and your editor's or agent app's env:

```bash
export GITHUB_TOKEN=github_pat_...
export GH_TOKEN=...
```

`GITHUB_TOKEN` is reserved for CI (GitHub Actions). Locally, use `gh auth login`.

### 3. GitHub MCP (Cursor)

In `~/.cursor/mcp.json`, **never hardcode a token**. Use a separate variable that cannot override gh:

```json
"github": {
  "url": "https://api.githubcopilot.com/mcp/",
  "headers": {
    "Authorization": "Bearer ${env:GITHUB_MCP_TOKEN}"
  }
}
```

Set the MCP token from your gh OAuth session (same scopes as the CLI):

```bash
# Add to ~/.zshrc — NOT named GITHUB_TOKEN
export GITHUB_MCP_TOKEN="$(gh auth token)"
```

Restart Cursor or T3 Code after changing MCP config or shell env.

### 4. GitHub MCP (Claude Code)

Add it at user scope. The single quotes keep the shell from expanding the variable, so the token never lands in `~/.claude.json`:

```bash
claude mcp add --transport http -s user github https://api.githubcopilot.com/mcp/ \
  --header 'Authorization: Bearer ${GITHUB_MCP_TOKEN}'
```

Check that `claude mcp list` shows `github` connected and `rg -o 'Bearer [^"]*' ~/.claude.json` prints `Bearer ${GITHUB_MCP_TOKEN}`, not a token.

### 5. If you must use a fine-grained PAT

Create one at [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) with **Repository access: this repo** and permissions:

| Permission | Access |
|------------|--------|
| Metadata | Read |
| Contents | Read and write |
| Pull requests | Read and write |
| Issues | Read and write |

Store it as `GITHUB_MCP_TOKEN`, not `GITHUB_TOKEN`.

## Account per repo

With more than one GitHub account, each repo can use its own. The login lives in a per-user file, not the committed `project.md`.

- **Where.** `~/.config/collective-wisdom/user.md`, outside the clone, so it can't be committed or lost when the clone is replaced.
- **What it holds.** GitHub logins and one dollar figure, never tokens. The shape is in `~/.collective-wisdom/templates/user.md`: a Settings table (the Claude subscription figure) and a GitHub accounts table with one row per repo.
- **Who writes it.** `set up this repo` will create the file and add the row (a later ticket, CW-163). Until then, copy the template to that path and add the row yourself. If the file exists, add a line under `## GitHub accounts`, with the backticks:

  ```
  | `github.com/acme/app` | `acme-login` |
  ```

  The first cell is the host and `owner/repo` of the repo's `origin` remote, in any case. The second is the gh login that acts in that repo. One row per repo: two rows for the same repo is an error. An SSH host alias (`git@work-gh:acme/app`) gives the host `work-gh`, which gh does not know, so use an https remote or the real host.
- **What `gh.sh` does.** In a repo with a row, `~/.collective-wisdom/scripts/gh.sh` gets that login's token with `gh auth token --user <login>` and gives it to that one `gh` command. It never runs `gh auth switch`, so the active account and `gh auth status` stay as they were. If the login is not signed in on that host, it stops with exit 2 and runs nothing; run `gh auth login -h <host>`. With no row, `gh.sh` runs `gh` as before.
- **The merge gate.** `merge_pr.py` and `cos_approve_pr.py` need the row and stop without one. A merge goes ahead only when the signed-in gh login is the mapped one (or a CODEOWNERS `*` user).
  The row in `user.md` is what the gate trusts, and the keyring login it names is the account `gh.sh` acts as, so protect that file like `.git/config`.
- **gh version.** `gh auth token --user` needs a recent gh. An old one fails with `unknown flag`, which `gh.sh` shows.

Verify with the last command in § Verify, run in each repo.

## Merge gate

With a Chief of Staff, a merge is approved by the user's own `approve N` reply in the Chief of Staff thread. `~/.collective-wisdom/scripts/cos_approve_pr.py` checks that message in T3's message store, that gh is signed in as the login `user.md` maps to this repo (§ Account per repo), and that the PR is open, not a draft, based on the merge target branch and still at the head the user saw. Only when it exits 0 does the Chief of Staff relay the approval to the merge child, naming that head. `~/.collective-wisdom/scripts/merge_pr.py` then merges only if gh is signed in as that login too and the PR's head still equals the relayed one, so a push after the approval needs a new `approve N` (or a new `--auto` pass, `chief-of-staff/approvals.md` § Auto-approval). The merge child stops with `BLOCKED: head moved after approval` on any other head, even one that only merges the merge target branch in. The one exception is a conflict resolution: with `Review after conflict resolution` (`project.md` § Identity) `off`, `~/.collective-wisdom/scripts/merge_pr.py` also merges a resolved head, a single merge commit whose first parent is the approved head, the only PR commit after it, with its second parent on the merge target branch, and carrying the `resolving conflicts with <target>` note from `open-pr` § Conflict resolution. `--auto` refuses a head that carries that note. In a hand run there is no relay and no `cos_approve_pr.py`: the user's own message in the run's thread, sent after the `MERGE READY` it approves, is the approval, and `~/.collective-wisdom/scripts/merge_pr.py` still merges only at that report's head.

With `Approval risk tolerance` (`project.md` § Identity) set to `balanced` or `permissive`, the Chief of Staff can run `~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto` instead. It runs every gate above except the user's message, and in its place needs the approval rule to say auto for the ticket's `Risk:` level and the setting on `origin/<target>` (the merge target branch), no PR file on the approval path, no renamed file, fewer than 100 files, no `flag:` or migration path, and no head that carries an unreviewed conflict-resolution note. It exits 0 only then, and the relay and `~/.collective-wisdom/scripts/merge_pr.py` work as before: CI, both review PASS comments (in `ci` review mode, no unresolved CI review thread instead) and the head are still checked at every setting. `--auto` (like `~/.collective-wisdom/scripts/merge_pr.py`) needs a gh whose `pr view --json files` returns `changeType`; with an older gh it exits 2 and the user decides.

Nothing in the team submits a GitHub review. The gate still needs no branch protection, ruleset or CODEOWNERS file. If you set those up and they require a review, `~/.collective-wisdom/scripts/merge_pr.py` stops and names the reviewers GitHub is waiting on. Keep in mind that GitHub does not let a PR's author approve it, so the owner's own PRs need another human's review. The exception is a codeowner: when the signed-in gh login is on the `*` line of `.github/CODEOWNERS` on `origin/<target>` (the merge target branch), `~/.collective-wisdom/scripts/merge_pr.py` (and `~/.collective-wisdom/scripts/cos_approve_pr.py`) accept that login besides the mapped login, and a PR whose only blocker is the missing review (`reviewDecision` `REVIEW_REQUIRED`, state `BLOCKED`) may merge. This relies on the ruleset's bypass list holding the repo admin role in `pull_request` mode, so GitHub itself refuses anyone else. Every other gate (checks, review PASS comments (in `ci` review mode, no unresolved CI review thread instead), closeout, head) still runs. `Require teammate approval` (`project.md` § Git and GitHub) adds a rule on top of the user's `approve N`: with it `on`, the gate also needs an approving review on the current head from someone other than the PR author who is an owner, member or collaborator of the repo (reviews from anyone else are ignored), and a standing changes-requested review from any teammate stops the merge. `approve N` stays required either way.

## Verify

```bash
# Should succeed (wrapper clears GITHUB_TOKEN)
~/.collective-wisdom/scripts/gh.sh api graphql -f query='{ viewer { login } }'

# Should return "main", not FORBIDDEN
~/.collective-wisdom/scripts/gh.sh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { defaultBranchRef { name } } }'

# Must print the login user.md maps to this repo (the active gh account when there is no row): every agent posts as this account
~/.collective-wisdom/scripts/gh.sh api user --jq .login
```
