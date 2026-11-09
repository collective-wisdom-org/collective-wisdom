# As-built: Check that Cursor loads the team subagents and fix what it rejects

**Shipped:** in PR #265
**Ticket:** CW-255
**Spec:** [2026-11-08-cw-255-cursor-subagents-design.md](../specs/2026-11-08-cw-255-cursor-subagents-design.md)

## Differs from the spec

- The spec lists AGENTS.md, the template, compatibility.md and project.md as the doc changes. Also changed: `README.md` (the install and layout lines), the team-docs trigger in `agent-team/docs/agents/documenter.md` (now also `.cursor/agents/`), and a note in `agent-team/docs/agents/org-chart.md`.
- The spec says one table-driven test in `test_agent_files.py`. There are two: the per-agent twin check and a check that both folders hold the same names.
- In `docs/agents/project.md` the path list also names `~/.cursor/rules` (the file `collective-wisdom.mdc`), which CW-252 added but left off the list.
- The five live Cursor runs did not happen: the Cursor agent CLI was not logged in. The compatibility cell and G4 say so.
