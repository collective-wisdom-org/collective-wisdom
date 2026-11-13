# As-built: Install the agent-gantt plugin from install.sh

**Shipped:** in PR #285
**Ticket:** CW-282
**Spec:** [2026-11-13-cw-282-install-agent-gantt-design.md](../specs/2026-11-13-cw-282-install-agent-gantt-design.md)

## Differs from the spec

- Spec § Docs adds only `~/.claude/plugins` to project.md § Security overlays. Shipped also lists `~/.claude.json`, `~/.claude/backups` (written by the `claude` CLI, even on a dry run through `claude plugin list`) and `CLAUDE_CONFIG_DIR`, which the user may set outside `$HOME`.
- Spec says a dry run's `claude plugin list` writes nothing of ours. On a machine where Claude Code never ran it may create `~/.claude.json`; README § Install on a machine says so and lists the two new `TODO:` cases.
- Spec § Tests uses an empty stub folder for the no-`claude` case. Shipped drops the PATH folders that hold a real `claude` and links their other programs into the stub folder, and in the other cases the stub shadows any real `claude`.
- A plugin install that fails with no output ends its to-do with `(it failed)` instead of `(it failed: <last line>)`.
