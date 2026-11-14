# As-built: shrink the Chief of Staff thread start

**Shipped:** in PR #321
**Ticket:** CW-314
**Spec:** [2026-11-14-cw-314-shrink-thread-start-design.md](../specs/2026-11-14-cw-314-shrink-thread-start-design.md)

## Differs from the spec

- The spec says `cos_models.py` prints both `target` and `modelSelection` for a role a thread passes. It prints only what the old tables defined: `chief` prints `modelSelection`, `ticket-helper`, `pm` and `spec` print `target`, and `build` prints both. The old text never defined the other combinations, so none was invented.
- `cos_models.py` accepts `-h` and `--help` (printing its docstring), because `test_symlinked_root.py` runs every script with `--help`.
- Where moved text said "the table" or "a row of this thread's table", it now says `cos_models.py` or names the role (`readiness.md`, `rotation.md`, `ticket-helper.md`, `continuation.md`, `startup.md`, `project-manager/reference.md`, `docs/agents/chief-of-staff.md`). `models.md` adds one sentence saying the Chief of Staff thread's own model is the one the user picks (startup.md step 3 checks) and that a rotation successor gets the `chief` role's `modelSelection`, since `cos_models.py` has no row for the user's pick.
