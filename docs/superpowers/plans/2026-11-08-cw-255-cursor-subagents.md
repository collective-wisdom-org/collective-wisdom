# CW-255 plan: Cursor-valid team subagents

Spec: `docs/superpowers/specs/2026-11-08-cw-255-cursor-subagents-design.md`. Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

1. Add `agent-team/.cursor/agents/{code-reviewer,compacter,documenter,implementer,security-reviewer}.md`: same `name`, `description` and body as the Claude file, `model: inherit`, no `tools`, `readonly: true` for code-reviewer, documenter and security-reviewer.
2. `install.sh`: link `agent-team/.cursor/agents/*` into `~/.cursor/agents/` with `mlink`; add `.cursor/agents` to the `mprune` list.
3. Tests: `test_agent_files.py` twin check over the five names; `test_install_machine.py` `world` fixture gets `.cursor/agents/ag.md`, fresh-install asserts the link, the kept/dead-link test covers a dead `~/.cursor/agents` link.
4. Docs: `AGENTS.md`, `agent-team/templates/AGENTS.md`, `docs/compatibility.md` (install note, Cursor Subagents cell, G4, "Last checked"), `docs/agents/project.md` security overlay path list.
5. Live runs in Cursor (`agent -p`): only if `agent status` is logged in; otherwise list as Not proven.
