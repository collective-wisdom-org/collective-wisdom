# collective-wisdom: Agent Instructions

All agents working on this repo must follow these rules.

## Product

**collective-wisdom** is the shared agent team: skills, scripts and role docs that move tickets from spec to merge, plus the `install.sh` that copies, updates and checks them in apps. The product is the agent team itself. There is no app stack.

- Shared files live in `agent-team/`, which mirrors a consuming repo. The root links into it so a Chief of Staff can run here against one copy. Edit under `agent-team/`, never through the root links.
- Repo-specific facts (tracker, its scope and prefix, commands, repo invariants): `docs/agents/project.md`. That file is local to this repo and is never shipped.

## Required reading

1. `docs/agents/project.md`: repo-specific config and invariants
2. `docs/agents/org-chart.md`: who is on the agent team and what each role may do
3. Your role file in `docs/agents/` (see `docs/agents/README.md`)
4. `docs/agents/security-review.md`: OWASP-aligned PR security review before merge (ship loop phase 4)

## GitHub

- Use `./scripts/gh.sh` for all `gh` commands (PRs, API, issues). Do not use bare `gh`. If you must, prefix it: `env -u GITHUB_TOKEN -u GH_TOKEN gh ...`.
- Never export a limited PAT as `GITHUB_TOKEN` locally. It overrides `gh auth login` and causes `Resource not accessible by personal access token` on GraphQL.
- Full setup: `docs/agents/github-auth.md`.

## Workflow

- Write or edit tickets with the `write-ticket` skill.
- **One ticket = one branch = one PR**
- Branch naming and ticket identifiers: see `docs/agents/project.md`
- Link the ticket in the PR description
- Move the ticket to **In Review** when PR is open, **Done** when merged
- Run the test command from `docs/agents/project.md` before opening a PR
- Do not expand scope beyond the assigned ticket

## Testing

Write tests for behavior that would hurt users if it broke without anyone noticing. Skip the rest.

Test:

- Script behavior the team relies on: state files, ranking, merge gates, the install copy rules
- Error paths that must not take down a Chief of Staff pass
- Link and layout checks that keep an installed app and this repo working (`test_root_links.py`)
- Tracker doc contracts the scripts parse

Don't test:

- Prose and copy in skills and docs
- Constants and registries (`assert TYPES == {...}`)
- Framework or library behavior

How:

- One table-driven test per rule, not one test per edge case
- A test must be able to fail for a real bug. Don't write tests that restate the implementation
- In review, a fix gets a new test only when it fixes a real bug
- Rough budget: test lines should not exceed the lines of feature code in the PR

## Secrets

- Never commit `.env`, API keys, or tokens

## Agent config

This file holds the shared instructions for every agent: Cursor, Claude Code, and T3 Code threads on either. `CLAUDE.md` imports it (`@AGENTS.md`).

- Project skills live in `agent-team/.claude/skills/`, reached at `.claude/skills/` through a root link. Cursor and Claude Code both load them. Codex discovers the same files through `.agents/skills`, a relative symlink to `../.claude/skills`.
- Project subagents live in `agent-team/.claude/agents/` (root link `.claude/agents`). Each is a short pointer to a role file in `docs/agents/`, which holds the real brief. On hosts that don't load that format, start a general subagent with the role file as its prompt.
- Always-on project rules go in this file, not in `.cursor/rules/`.
- Who's on the agent team and what each role may do: `docs/agents/org-chart.md`.

## Commits

- Conventional commits: `feat:`, `fix:`, `docs:`, `infra:`
- Small, focused commits preferred
