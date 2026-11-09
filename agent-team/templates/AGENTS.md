# <Project>: Agent Instructions

All agents working on this repo must follow these rules.

## Product

**<Project>** is <one line>.

- Stack: <stack>. Update this section and `docs/agents/project.md` as it changes.
- Repo-specific facts (tracker, its scope and prefix, commands, repo invariants): `docs/agents/project.md`.

## Required reading

1. `docs/agents/project.md`: repo-specific config and invariants
2. `~/.collective-wisdom/docs/agents/org-chart.md`: who is on the agent team and what each role may do
3. Your role file in `~/.collective-wisdom/docs/agents/` (see `~/.collective-wisdom/docs/agents/README.md`)
4. `~/.collective-wisdom/docs/agents/security-review.md`: OWASP-aligned PR security review before merge (ship loop phase 4)

## GitHub

- Use `~/.collective-wisdom/scripts/gh.sh` for all `gh` commands (PRs, API, issues). Do not use bare `gh`. If you must, prefix it: `env -u GITHUB_TOKEN -u GH_TOKEN gh ...`.
- Never export a limited PAT as `GITHUB_TOKEN` locally. It overrides `gh auth login` and causes `Resource not accessible by personal access token` on GraphQL.
- Full setup: `~/.collective-wisdom/docs/agents/github-auth.md`.

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

- The machine install links the team's skills into `~/.claude/skills` (Claude Code), `~/.agents/skills` (Codex) and `~/.cursor/skills` (Cursor), and its subagents into `~/.claude/agents` and `~/.cursor/agents`. An app may still hold its own skills in `.claude/skills/`.
- Each team subagent is a short pointer to a role file in `~/.collective-wisdom/docs/agents/`, which holds the real brief. Cursor gets copies with the same name, description and body, the matching Cursor model in `model:` (`grok-4.7` for `opus`, `composer-2.5` for `sonnet`), and `readonly: true` on reviewers. Elsewhere, start a general subagent with the role file as its prompt.
- The agent team (skills, subagents, scripts, role docs) is installed once per machine from the collective-wisdom clone with `install.sh`. Update it by checking out a newer release there and rerunning `./install.sh`. Only `docs/agents/project.md` lives in this repo. Change shared files in collective-wisdom.
- Always-on project rules go in this file, not in `.cursor/rules/`.
- Who's on the agent team and what each role may do: `~/.collective-wisdom/docs/agents/org-chart.md`.

## Commits

- Conventional commits: `feat:`, `fix:`, `docs:`, `infra:`
- Small, focused commits preferred
