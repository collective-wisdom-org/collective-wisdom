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

`<owner>/<repo>` is the repo in [`project.md`](project.md) § Git and GitHub. Run gh through the repo wrapper (`ship-loop` § Repo invariants), which clears the env vars:

```bash
./scripts/gh.sh pr create ...
./scripts/gh.sh api repos/<owner>/<repo>
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

## Agent users

By default every agent acts as your gh account, so PRs, review comments and tickets look like you wrote them. Optionally the team works as four GitHub users, one per persona in [`personas.md`](personas.md): the Chief of Staff, the builder, the code reviewer and the security reviewer. Each login lives in [`project.md`](project.md) § Git and GitHub; a row left as `none` keeps that role on the active gh account.

### Set up

1. Create four GitHub accounts, one per persona. Use the suggested logins in `personas.md` or others.
2. Set each profile from `personas.md` (name and the one-line bio).
3. From your own account, invite each as a collaborator on the repo. A personal repo only offers write access, so every agent user can push and its tickets count as team tickets. Turn on two-factor sign-in for each account, and accept each invite while signed in as that account.
4. Add each account to your gh keyring with `gh auth login -h github.com -p https`, signing in as that account; gh keeps each token in the system keyring. `gh.sh` needs gh 2.40 or newer for `gh auth token -u`; an older gh reports "no gh login" for every role.
5. Adding an account makes it the active one. Switch back with `gh auth switch -u <owner login>`. `scripts/merge_pr.py` refuses to run while the active account is one of the four agent users.
6. Fill the four login rows in `project.md` with the new logins.
7. Set `git config --global user.email` to an address on your own GitHub account (a verified email or your noreply address), so the commits you make by hand link to you.
8. Run the checks under Verify.

### How a role picks its account

`./scripts/gh.sh` reads one environment variable, `AGENT_GH_ROLE`, set per command because agent shells keep no environment variables between commands:

```bash
AGENT_GH_ROLE=builder ./scripts/gh.sh pr view 12
```

The roles are `chief-of-staff`, `builder`, `code-reviewer` and `security-reviewer`.

- Unset or empty: the active gh account, as before.
- A role whose `project.md` row is `none`: the active gh account.
- A role with a login: that one `gh` call gets the login's token from the keyring (`gh auth token -u <login>`) as `GH_TOKEN`. The token is not written to a file, printed or exported beyond that process. Nothing sets `GITHUB_TOKEN`.
- An unknown role, a bad login in `project.md` or a login the keyring does not have: `gh.sh` exits 2 with one line on stderr and makes no `gh` call. It never falls back to your account, so a wrong setup cannot quietly post as you.

Scripts that call `gh.sh` inherit the role from their environment. Merges stay on your own login: `scripts/merge_pr.py` runs with no role, so the merge and the branch delete are yours and the agent users never merge. The builder's commits and pushes on a ticket branch go through `scripts/git.sh`, which authors them with the builder's GitHub noreply address and pushes with its keyring token. Git's credential helper fetches the token on demand, for https://github.com only, and it is never exported, written to git config or a file, or put in the remote URL. A `none` row keeps your git config and credential, and commits you make by hand keep your own git config. `git.sh` refuses a push to any remote that is not https://github.com (ssh, `git://`, an unconfigured URL) or that holds a commit not authored as the builder, since that would use your machine's key or identity. This check is a guardrail against mistakes, not a boundary: an alias or `rebase --exec 'git push'` can get past it.

The trust checks follow the same rule. A team comment counts when its author is the login of the role that writes it, or the active gh account when that row is `none`. Once the reviewer rows are set, a review comment posted earlier as your own account no longer counts, so reviews on open PRs must run again.

## Merge gate

A merge is approved by the owner's approving review on GitHub. When the user replies `approve N` in the Chief of Staff thread, `scripts/cos_approve_pr.py` posts that review as the owner, after it has checked the user's own message in T3's message store; approving by hand on GitHub still works. `scripts/merge_pr.py` refuses to merge without an approving review by the owner login (`project.md` § Git and GitHub, `Owner login`) on the PR's current head, and without branch protection on `main` that requires an approving review. A push after the approval, or a later changes-requested review, voids it: approve again. The `approve N` reply routes the merge child; the review is the proof. The one-time setup below (CODEOWNERS, branch protection with stale approvals dismissed) is unchanged and still required.

GitHub does not let a PR's author approve it, so PRs must be opened by the builder user (§ Agent users), not the owner. The gate cannot pass without that setup.

The owner sets this up once, by hand. No agent changes GitHub settings.

1. Add `.github/CODEOWNERS` with one line, `* @<owner login>`, and merge it.
2. Settings → Branches → add a branch protection rule for `main`:
   - Require a pull request before merging, with 1 required approval.
   - Dismiss stale pull request approvals when new commits are pushed.
   - Require review from Code Owners. Only the owner's approval then satisfies the rule, not an agent user's (the agent users have write access).
   - Require status checks to pass, using the repo's required checks (`project.md` § Commands). Leave "require branches to be up to date" off.
   - Do not allow bypassing the above settings (enforce for admins), since the merge runs as the owner.
3. Check it:

```bash
./scripts/gh.sh api repos/<owner>/<repo>/branches/main/protection --jq .required_pull_request_reviews.required_approving_review_count
```

It prints `1`. A 404 means `main` is not protected; `merge_pr.py` then stops with `main has no branch protection requiring an approving review`.

## Verify

```bash
# Should succeed (wrapper clears GITHUB_TOKEN)
./scripts/gh.sh api graphql -f query='{ viewer { login } }'

# Should return "main", not FORBIDDEN
./scripts/gh.sh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { defaultBranchRef { name } } }'

# With agent users set up, each role must print its own login from project.md
for role in chief-of-staff builder code-reviewer security-reviewer; do
  AGENT_GH_ROLE=$role ./scripts/gh.sh api user --jq .login
done

# With no role it must print your own login (the owner), not an agent user
./scripts/gh.sh api user --jq .login

# The builder's commit identity: its name and noreply email (<id>+<login>@users.noreply.github.com)
AGENT_GH_ROLE=builder ./scripts/git.sh var GIT_AUTHOR_IDENT
```
