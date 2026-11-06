# As-built: Resolve merge conflicts in the merge lane without restarting the review loop

**Shipped:** in PR #142
**Ticket:** CW-138
**Spec:** [2026-11-05-cw-138-conflict-resolution-stage-design.md](../specs/2026-11-05-cw-138-conflict-resolution-stage-design.md)

## Differs from the spec

- The spec said `scripts/cos_approve_pr.py --auto` already refuses on any `flag:` line. It does not: it checks file paths, not the lines `cos_brief.py pr` prints. `cos_approve_pr.py` now also stops with `PR needs the user: conflict resolution not reviewed` when the head carries the conflict note.
- `merge_pr.py` also asks git that the head be the only commit not already in the approved head or `origin/main` (`git rev-list <head> ^<first parent> ^origin/main`), so the merge's second parent must be on `main`. The spec only said the head is the only PR commit after the approved head. It reads the head's parents with `pr_diff_delta.fetch` and `git rev-list --parents`. When either read fails, the head is treated as not a resolved head, so the merge stops as for any other head.
- `cos_brief.py` keeps its own copy of the conflict-note pattern, as it does for the main-merge note, instead of importing it from `merge_pr.py`.
- When a conflict is resolved before any approval and the user approves the resolved head itself, `merge_pr.py` takes the conflict note as covering the old reviews. The first draft only handled an approval of the first parent, which would have refused that merge.
