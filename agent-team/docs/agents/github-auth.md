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

## Agent users

By default every agent acts as your gh account, so PRs, review comments and tickets all look like you wrote them. The team can instead work as four GitHub users, one per persona in [`personas.md`](personas.md): the Chief of Staff, the builder, the code reviewer and the security reviewer. This is optional. Each login lives in [`project.md`](project.md) § Git and GitHub, and a row left as `none` keeps that role on the active gh account.

### Set up

1. Create four GitHub accounts, one per persona. Use the suggested logins in `personas.md` or others.
2. Set each profile from `personas.md` (name and the one-line bio).
3. From your own account, invite each as a collaborator on the repo with write access. Accept each invite while signed in as that account.
4. Add each account to your gh keyring with `gh auth login -h github.com -p https`, signing in as that account. gh keeps each token in the system keyring.
5. Adding an account makes it the active one. Switch back with `gh auth switch -u <owner login>`.
6. Fill the four login rows in `project.md` with the new logins.
7. Run the checks under Verify.

### How a role picks its account

`./scripts/gh.sh` reads one environment variable, `AGENT_GH_ROLE`, set per command because agent shells do not keep environment variables between commands:

```bash
AGENT_GH_ROLE=builder ./scripts/gh.sh pr view 12
```

The roles are `chief-of-staff`, `builder`, `code-reviewer` and `security-reviewer`.

- Unset or empty: the active gh account, as before.
- A role whose `project.md` row is `none`: the active gh account.
- A role with a login: that one `gh` call gets the login's token from the keyring (`gh auth token -u <login>`) as `GH_TOKEN`. The token is not written to a file, not printed and not exported beyond that process. Nothing sets `GITHUB_TOKEN`.
- An unknown role, a bad login in `project.md` or a login the keyring does not have: `gh.sh` exits 2 with one line on stderr and makes no `gh` call. It does not fall back to your account, so a wrong setup cannot quietly post as you.

Scripts that call `gh.sh` inherit the role from their environment. Merges stay on your own login: `scripts/merge_pr.py` runs with no role, so the merge and the branch delete are yours, and the agent users never merge. Commits and pushes also keep your own git config and gh credential.

The trust checks follow the same rule. A team comment counts when its author is the login of the role that writes it, or the account running the check when that row is `none`. Once the reviewer rows are set, a review comment posted earlier as your own account no longer counts, so reviews on open PRs have to run again.

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
```
