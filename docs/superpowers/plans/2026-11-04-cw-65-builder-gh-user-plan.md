# CW-65 plan: builder GitHub user

Spec: [2026-11-04-cw-65-builder-gh-user-design.md](../specs/2026-11-04-cw-65-builder-gh-user-design.md).

1. Check access: `AGENT_GH_ROLE=builder ./scripts/gh.sh api repos/dbeallor/collective-wisdom --jq .permissions` shows `push: true`. Stop with `BLOCKED:` if not.
2. `docs/agents/project.md`: set the Builder login row to `collective-wisdom-builder`. Keep the cell's note. Change nothing else.
3. Verify from the worktree: the Verify block in `docs/agents/github-auth.md` prints the right login per role, `./scripts/gh.sh pr list --state open` shows no `Head moved to` notes to repost, and `python3 -I -m pytest -q agent-team/scripts` passes.
4. Commit and open the PR with `AGENT_GH_ROLE=builder`, so the PR author proves the setup.
