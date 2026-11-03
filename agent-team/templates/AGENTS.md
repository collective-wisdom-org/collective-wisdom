# <Project>: Agent Instructions

All agents working on this repo must follow these rules.

## Product

**<Project>** is <one line>.

- Stack: <stack>. Update this section and `docs/agents/project.md` as it changes.
- Repo-specific facts (Linear team and prefix, commands, repo invariants): `docs/agents/project.md`.

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

- Write or edit Linear tickets with the `write-ticket` skill.
- **One Linear issue = one branch = one PR**
- Branch naming and Linear identifiers: see `docs/agents/project.md`
- Link the Linear issue in the PR description
- Move Linear issue to **In Review** when PR is open, **Done** when merged
- Run the test command from `docs/agents/project.md` before opening a PR
- Do not expand scope beyond the assigned Linear issue

## Testing

Write tests for behavior that would hurt users if it broke without anyone noticing. Skip the rest.

Test:

- Data scoping by owner: one user never sees or changes another's rows
- Auth: protected routes reject missing or bad tokens
- Money, prices and currency logic
- Concurrency, transactions and rollbacks
- Error paths that must not take down a job or a request
- API contracts: status codes and response shapes the frontend relies on

Don't test:

- Styling, layout and copy
- Small UI interactions: Escape to close, outside click, badge caps
- Constants and registries (`assert TYPES == {...}`)
- Framework or library behavior

How:

- One table-driven test per rule, not one test per edge case
- A test must be able to fail for a real bug. Don't write tests that restate the implementation
- In review, a fix gets a new test only when it fixes a real bug
- Rough budget: test lines should not exceed the lines of feature code in the PR

## Secrets

- Never commit `.env`, API keys, or tokens
- Use `.env.example` for documented variables

## Agent config

This file holds the shared instructions for every agent: Cursor, Claude Code, and T3 Code threads on either. `CLAUDE.md` imports it (`@AGENTS.md`).

- Project skills live in `.claude/skills/`. Cursor and Claude Code both load them. Codex discovers the same files through `.agents/skills`, a relative symlink to `../.claude/skills`; keep `.claude/skills/` as the source of truth.
- Project subagents live in `.claude/agents/`. Each is a short pointer to a role file in `docs/agents/`, which holds the real brief. On hosts that don't load that format, start a general subagent with the role file as its prompt.
- The agent team (skills, scripts, shared docs) is installed from the collective-wisdom repo with its `install.sh`. Change shared files there, not here.
- Always-on project rules go in this file, not in `.cursor/rules/`.
- Who's on the agent team and what each role may do: `docs/agents/org-chart.md`.

## Commits

- Conventional commits: `feat:`, `fix:`, `docs:`, `infra:`
- Small, focused commits preferred
