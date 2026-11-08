# As-built: CW-206 conflict at MERGE READY goes to the merge lane

**Shipped:** in PR #210
**Ticket:** CW-206
**Spec:** [2026-11-08-cw-206-conflict-merge-lane-design.md](../specs/2026-11-08-cw-206-conflict-merge-lane-design.md)

## Differs from the spec

- The spec says the `conflict-stand` stage op carries `noApproval`. A continuation has no stage op, so `cos_route.py` also prints a `set: {"noApproval": true}` line for `route: continuation`. `continuation.md` saves its keys with the new child, and `SKILL.md` § Send or queue applies them when the continuation falls back to the old child.
- A rebuilt `merge` or `merge-queued` ticket (`startup.md`) gets `noApproval` set, since a missing key reads as an approval. The spec does not cover a rebuild.
- `noApproval` takes `true` only. The spec says `true` or `null`; `cos_state.py` rejects `null`, so the key cannot be cleared inside the merge lane (a stage op to another stage still drops it).
