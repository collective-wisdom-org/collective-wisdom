# As-built: context compacter agent

**Shipped:** in PR #154
**Ticket:** CW-72
**Spec:** [2026-11-04-cw-72-context-compacter-design.md](../specs/2026-11-04-cw-72-context-compacter-design.md)

## Differs from the spec

- The spec compares against `origin/main`. `compact_check.py` defaults to the merge target branch from `project.md` (CW-125 landed after the spec). `--base <ref>` still overrides it.
- The spec says a solo build leaves the compaction unreviewed and uncommitted. `build-from-plan` has no solo split, so the pass always commits `docs: compact agent text for <PREFIX>-N` and pushes.
- Bad arguments to `compact_check.py` exit 2 with `compact: cannot read arguments`, so `test_symlinked_root.py` lists it with the other scripts that do.
- The role file has a root link at `docs/agents/compacter.md`, which `test_root_links.py` requires.
