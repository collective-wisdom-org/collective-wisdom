# As-built: Resolve a conflict instead of waiting for CI that cannot start

**Shipped:** in PR #454
**Ticket:** WISE-439
**Spec:** [2026-11-15-wise-439-resolve-conflict-before-ci-wait-design.md](../specs/2026-11-15-wise-439-resolve-conflict-before-ci-wait-design.md)

## Differs from the spec

- The spec puts the Chief of Staff **Conflict** step in `chief-of-staff/SKILL.md` § Child path. It shipped as `chief-of-staff/sweep.md` § Conflict relay, with a one-line pointer in SKILL.md, because the SKILL.md core is capped by the compaction budget test.
- `conflictHead` is also documented in `chief-of-staff/state-keys.md`.
- `wait-for-ci.sh` reads a garbled merge-state answer (not two uppercase words) as "not a conflict" and keeps polling.
- `cos_ready_check.load_prs` no longer takes a `mode` argument: the PR list always asks for `statusCheckRollup` and the merge state.
- On a conflict, a failed `project_config.py target` read ends the wait with exit 2 (`cannot read project.md`), not exit 3.
