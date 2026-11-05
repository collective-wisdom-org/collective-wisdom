# CW-127 plan: teammate approval and GitHub's required reviews in the merge gate

Spec: [2026-11-05-cw-127-teammate-approval-design.md](../specs/2026-11-05-cw-127-teammate-approval-design.md). Paths are under `agent-team/` unless noted. `main` already has CW-58 (#131) merged in; PR #132 (CW-125) is still open and touches the same files, so keep the new lines apart from its lines (see the spec's section on #132).

1. `scripts/merge_pr.py`:
   - Add `author,reviews,reviewDecision,reviewRequests` to `FIELDS`.
   - In `read_facts`, set `f["teammate"]` from `project_config.value("Require teammate approval")` (lower-cased; `None` or `off` is off, `on` is on, anything else kept as is so the gate can stop on it).
   - Add `required_reviews(f)` and `teammate_approval(f)` returning a stop reason or None, and call them in `gate()` after the approved-head check and before the mergeability check. Required reviews first, then the teammate row. Rules and stop lines exactly as the spec says. Names: a user is `login`; a team (`__typename` `Team`) is `@<owner>/<slug>`, with `<owner>` from `project_config.repo()`.
   - Update the module docstring only if it lists gates.
2. `templates/project.md`: add the `Require teammate approval` row after `Owner login`.
3. `scripts/test_merge_pr.py`: extend `green()` with `author`, `reviews`, `reviewDecision`, `reviewRequests`, `teammate`. Add two table-driven tests at the end of the file: the teammate rule and required reviews (rows listed in the spec's Tests section). Each row must be able to fail for a real bug.
4. Docs (prose, no tests): `.claude/skills/ship-loop/SKILL.md` `MERGE READY` block gets `Reviews needed:` after `Security review PASS:` (and the sentence on how to read it); `.claude/skills/chief-of-staff/approvals.md` merge block gets `GitHub reviews:` under `Reviews:`; `.claude/skills/merge-pr/SKILL.md` Pre-merge checks list; `docs/agents/github-auth.md` § Merge gate last paragraph.
5. Verify: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
6. Open the PR, closeout docs, docs check, code review, security review, per ship-loop § Team mode.
