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

## Merge gate

A merge is approved by the user's own `approve N` reply in the Chief of Staff thread. `scripts/cos_approve_pr.py` checks that message in T3's message store, that gh is signed in as the owner (`project.md` § Git and GitHub, `Owner login`), and that the PR is open, not a draft, based on `main` and still at the head the user saw. Only when it exits 0 does the Chief of Staff relay the approval to the merge child, naming that head. `scripts/merge_pr.py` then merges only if gh is signed in as the owner too and the PR's head still equals the relayed one, so a push after the approval needs a new `approve N` (or a new `--auto` pass, `chief-of-staff/approvals.md` § Auto-approval). The merge child stops with `BLOCKED: head moved after approval` on any other head, even one that only merges `main` in.

With `Approval risk tolerance` (`project.md` § Identity) set to `balanced` or `permissive`, the Chief of Staff can run `scripts/cos_approve_pr.py <PREFIX>-N --auto` instead. It runs every gate above except the user's message, and in its place needs the approval rule to say auto for the ticket's `Risk:` level and the setting on `origin/main`, no PR file on the approval path, no renamed file, fewer than 100 files, and no `flag:` or migration path. It exits 0 only then, and the relay and `scripts/merge_pr.py` work as before: CI, both review PASS comments and the head are still checked at every setting.

Nothing in the team submits a GitHub review, and the gate needs no branch protection, ruleset or CODEOWNERS file. If you set those up anyway, keep in mind that GitHub does not let a PR's author approve it, so the owner's own PRs would need another human's review.

## Verify

```bash
# Should succeed (wrapper clears GITHUB_TOKEN)
./scripts/gh.sh api graphql -f query='{ viewer { login } }'

# Should return "main", not FORBIDDEN
./scripts/gh.sh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { defaultBranchRef { name } } }'

# Must print the owner login from project.md: every agent posts as this account
./scripts/gh.sh api user --jq .login
```
