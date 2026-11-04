# CW-71 plan: publish release notes to a release-notes branch

Spec: [2026-11-04-cw-71-publish-release-notes-design.md](../specs/2026-11-04-cw-71-publish-release-notes-design.md).

1. `agent-team/scripts/release_notes.py`: move the sort and text out of `main()` into `render(files, prs)`. `main()` reads the working tree and gh, calls it, prints, keeps its exit codes. Printed output and existing tests unchanged.
2. `agent-team/scripts/merge_pr.py`: add an optional `input` argument to `run`, add `publish(pr, run)` (never raises, prints `merge-pr: warn <reason>`), call it after `cleanup()` on both the merge and already-merged paths, before the last line.
3. `agent-team/scripts/test_merge_pr.py`: the three tests in the spec's Tests section (table-driven publish, git objects only with a real temp repo, failed publish keeps exit 0 and the last line).
4. Docs and rules: `docs/agents/project.md` and `agent-team/templates/project.md` (§ Repo invariants exception, § Docs row), `agent-team/.claude/skills/merge-pr/SKILL.md` (§ Merge, Closeout in PR), root `README.md`, `agent-team/docs/agents/README.md`, `agent-team/docs/superpowers/README.md` § Release notes.
5. Verify: `python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
