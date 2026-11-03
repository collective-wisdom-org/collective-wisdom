# GitHub auth for agents

Agents and local scripts need GitHub API access for PRs, issues, and the GitHub MCP server. A recurring failure mode is a **limited fine-grained PAT** exported as `GITHUB_TOKEN`, which overrides `gh auth login` and breaks PR creation.

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

`<owner>/<repo>` is the repo in [`project.md`](project.md) § Git and GitHub. Always run gh through the repo wrapper (or unset the env vars yourself):

```bash
./scripts/gh.sh pr create ...
./scripts/gh.sh api repos/<owner>/<repo>
```

### 2. Do not export GITHUB_TOKEN globally

Remove any of these from `~/.zshrc`, `~/.zprofile`, or your editor's or agent app's env:

```bash
export GITHUB_TOKEN=github_pat_...
export GH_TOKEN=...
```

`GITHUB_TOKEN` is reserved for CI (GitHub Actions). Local dev should use `gh auth login`.

### 3. GitHub MCP (Cursor)

In `~/.cursor/mcp.json`, **never hardcode a token**. Use a separate variable so it cannot override gh:

```json
"github": {
  "url": "https://api.githubcopilot.com/mcp/",
  "headers": {
    "Authorization": "Bearer ${env:GITHUB_MCP_TOKEN}"
  }
}
```

Set the MCP token from your gh OAuth session (same scopes as CLI):

```bash
# Add to ~/.zshrc — NOT named GITHUB_TOKEN
export GITHUB_MCP_TOKEN="$(gh auth token)"
```

Restart Cursor or T3 Code after changing MCP config or shell env.

### 4. GitHub MCP (Claude Code)

Add it at user scope. The single quotes stop the shell from expanding the variable, so the token never lands in `~/.claude.json`:

```bash
claude mcp add --transport http -s user github https://api.githubcopilot.com/mcp/ \
  --header 'Authorization: Bearer ${GITHUB_MCP_TOKEN}'
```

Check that `claude mcp list` shows `github` connected, and that `rg -o 'Bearer [^"]*' ~/.claude.json` prints `Bearer ${GITHUB_MCP_TOKEN}`, not a token.

### 5. If you must use a fine-grained PAT

Create one at [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) with **Repository access: this repo** and permissions:

| Permission | Access |
|------------|--------|
| Metadata | Read |
| Contents | Read and write |
| Pull requests | Read and write |
| Issues | Read and write |

Store it as `GITHUB_MCP_TOKEN`, not `GITHUB_TOKEN`.

## Verify

```bash
# Should succeed (wrapper clears GITHUB_TOKEN)
./scripts/gh.sh api graphql -f query='{ viewer { login } }'

# Should return "main", not FORBIDDEN
./scripts/gh.sh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { defaultBranchRef { name } } }'
```
