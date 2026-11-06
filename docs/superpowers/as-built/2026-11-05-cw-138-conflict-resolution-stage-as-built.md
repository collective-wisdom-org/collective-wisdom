# As-built: Resolve merge conflicts in the merge lane without restarting the review loop

**Shipped:** in PR #PRNUM
**Ticket:** CW-138
**Spec:** [2026-11-05-cw-138-conflict-resolution-stage-design.md](../specs/2026-11-05-cw-138-conflict-resolution-stage-design.md)

## Differs from the spec

- The spec said `scripts/cos_approve_pr.py --auto` already refuses on any `flag:` line. It does not: it checks file paths, not the lines `cos_brief.py pr` prints. `cos_approve_pr.py` now also stops with `PR needs the user: conflict resolution not reviewed` when the head carries the conflict note.
- `cos_brief.py` keeps its own copy of the conflict-note pattern, as it does for the main-merge note, instead of importing it from `merge_pr.py`.
