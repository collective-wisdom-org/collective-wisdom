# Contributing

- Open an issue first for anything beyond a small fix.
- One ticket = one branch = one PR. Name the branch `feat/cw-N-short-title`.
- Edit shared files under `agent-team/`, never through the root links (`.claude/skills`, `scripts`, and so on). `docs/agents/project.md` is this repo's own config and is not shipped.
- Before you open a PR, run:

  ```
  uvx pytest -q agent-team/scripts
  shellcheck install.sh tag-release.sh agent-team/scripts/*.sh
  ```

- Use conventional commits: `feat:`, `fix:`, `docs:`, `infra:`.
- The PR body links the ticket. It has a `## Release note` section (one to three sentences for a user of the agent team) and a `## Proof` section with a `Not proven` list. See [agent-team/.claude/skills/open-pr/SKILL.md](agent-team/.claude/skills/open-pr/SKILL.md), section Proof.
- Prose follows the `human-writing` skill: plain sentences, no em dashes.
- Never commit `.env`, API keys or tokens.
