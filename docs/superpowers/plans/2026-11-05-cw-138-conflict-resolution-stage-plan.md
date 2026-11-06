# CW-138 plan: resolve conflicts in the merge lane without restarting the review loop

Spec: [2026-11-05-cw-138-conflict-resolution-stage-design.md](../specs/2026-11-05-cw-138-conflict-resolution-stage-design.md). Paths are under `agent-team/` unless noted. Read the spec first; it has the rules and the stop lines.

1. `scripts/project_config.py`: add `review_after_conflict(run=_git)` returning `"off"` or `"on"`, read from `origin/main` like `approval_setting`. Missing row is `off`; unknown value or unreadable file is `on`. Row name: `Review after conflict resolution`.
2. `scripts/merge_pr.py`:
   - Parse the note `Head moved to <H'> by resolving conflicts with main; reviews from <H> stand.` (second regex beside `NOTE`; by the gh login running the merge, naming the current head).
   - In `gate()`, the approved-head check also passes when the head is a resolved head of the approved head: setting `off`, the note present, the head a merge commit with two parents whose first is the approved head, and the only PR commit after the approved head. Read parents with git (fetch the PR head first, as `real_delta` does).
   - `stands()` accepts the same note for a review posted on the approved head.
   - Any other head stays `head ... is not approved head ...`.
3. `scripts/cos_brief.py`: `pr` prints `conflict: yes` when `mergeable` is `CONFLICTING`, and `flag: conflict resolution not reviewed` when the head carries the conflict note. Check that `scripts/cos_approve_pr.py --auto` already refuses on any `flag:` line; do not change that script unless it does not.
4. `templates/project.md` and `../docs/agents/project.md` (repo root `docs/agents/project.md`): add the `Review after conflict resolution (`off` or `on`)` row to § Identity after the approval risk tolerance row, value `off` in both, text as in the spec. Mind the "first backticked token" rule in project.md's header.
5. Tests, table-driven, one per rule (`AGENTS.md` § Testing), in `scripts/test_merge_pr.py`, `scripts/test_project_config.py` and the `cos_brief` test file (create it only if none exists): rows as the spec's § Tests lists. Each row must be able to fail for a real bug.
6. Docs (prose, no tests), per the spec's § Skills and docs: `open-pr` (new § Conflict resolution; step 1 points to it), `ship-loop` (phases 4 and 5, § Approvals, § Phase gates, the `MERGE READY` block's `Conflict resolved:` line), `merge-pr` § Head moved, `chief-of-staff/SKILL.md` § Send or queue (both relays, caller rows, head check keeps or withdraws the approval by setting) and § Full pass (the `BLOCKED:` conflict check), `chief-of-staff/approvals.md` (`conflict: yes`, merge block Risks line), `docs/agents/github-auth.md` merge paragraph, `org-chart.md` where it describes the head-moved path. `test_section_pointers.py` checks `§` pointers.
7. Verify: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
8. Open the PR, closeout docs, docs check, code review, security review, per `ship-loop`.
