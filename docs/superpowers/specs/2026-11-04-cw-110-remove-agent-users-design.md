# Remove the per-agent GitHub users (design)

**Status:** Shipped
**Shipped:** in PR #111, as specified
**Ticket:** CW-110

## Intent

CW-38, CW-65, CW-75, CW-77 and CW-92 gave each role its own GitHub account, and CW-52 and CW-87 built the merge gate on it: the builder opens the PR so the owner can post an approving review. The user asked to drop the accounts. Every agent goes back to acting as the account running `gh`, and the user's `approve N` in the Chief of Staff thread is the merge proof again.

## Design

- `scripts/gh.sh` clears `GITHUB_TOKEN` and `GH_TOKEN` and runs `gh`. `AGENT_GH_ROLE` is not read. `scripts/git.sh` is deleted: commits and pushes use plain git.
- `project_config.py` loses `ROLE_ROWS`, `LOGIN_RE`, `role_login` and the `login` command. The four login rows leave `docs/agents/project.md` and `agent-team/templates/project.md`. `Owner login` stays: `cos_approve_pr.py` still checks that gh is signed in as the owner.
- `merge_pr.py` counts the `## Code review`, `## Security review` and `Head moved to` comments from the running login, and drops `read_protection`, `owner_approval` and the agent-user check. `cos_brief.py` and `cos_handoff.py` do the same through `cos_brief.own_login()`.
- `cos_approve_pr.py` keeps its gates (root checkout, state, the user's message in T3's store, owner login, PR open and not a draft, base `main`, head unchanged) and posts nothing. Exit 0 prints `cos-approve: verified approve N for #PR at <SHA>`; the Chief of Staff relays only after that, and `merge_pr.py` merges only at the head the relay names.
- `docs/agents/personas.md` is deleted. `github-auth.md` loses § Agent users; § Merge gate now describes the thread approval and says no branch protection, ruleset or CODEOWNERS file is needed. The skills drop every per-role rule.

## Calls I made

- Branch protection, CODEOWNERS and the four accounts stay in GitHub for the owner to remove by hand. Nothing in the team changes GitHub settings.
- The script keeps the name `cos_approve_pr.py` so the Chief of Staff skill's command lines don't change.

## Verification

`uvx pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`, and `grep -rn AGENT_GH_ROLE agent-team docs/agents` returns nothing.
