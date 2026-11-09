# Compatibility

What the agent team does on each harness and each ticket tracker, and where it does not. Read this before you adopt the team on a setup other than Claude Code in T3 Code with GitHub Issues. It is this repo's own page and is not shipped to apps.

Last checked against the code on 2026-11-08.

## Legend

| Value | Meaning |
|---|---|
| 🟢 works | The code shows it, or the team runs it today. A run that no doc records is named in a note |
| 🟡 partial | Part of it works. The cell says what does not |
| 🔴 not supported | Nothing here makes it work on this column |
| ⚪ untested | Nothing shows it either way: the code does not show it and the team does not run it |

A cell is `works` only where the code shows it or the team runs it today. Anything not shown either way is `untested`.

Each cell starts with a colored circle so a column reads at a glance: 🟢 works, 🟡 partial, 🔴 not supported, ⚪ untested. GitHub markdown tables cannot color a cell, so the circle is only a visual aid. The word after it is the source of truth.

A cell that is not `works` gives a short reason and a gap number such as `G3`. The [Gaps](#gaps) list holds one line per gap with its ticket link, or `none yet` while there is no ticket.

The team needs GitHub for code on every tracker. The PR flow, the merge gate and the CI wait call `~/.collective-wisdom/scripts/gh.sh` whatever the tracker is. Other code hosts are out of scope.

## Matrix 1: harnesses

Columns are the places a person runs an agent session. Each column is a T3 Code thread running that harness. The team is built for T3 Code, so sessions without it are not covered.

| Feature | Claude Code in T3 Code | Codex in T3 Code | Cursor in T3 Code | Antigravity in T3 Code |
|---|---|---|---|---|
| Install (skills and instruction block) | 🟢 works | 🟢 works | 🟡 partial: rule file written, no Cursor thread seen reading it (G1) | 🔴 not supported: `install.sh` writes nothing for it (G17) |
| Team skills load | 🟢 works | ⚪ untested (G2) | ⚪ untested (G3) | ⚪ untested (G18) |
| Subagents | 🟢 works | ⚪ untested: role file as prompt (G4) | 🟡 partial: Cursor-valid copies installed, no Cursor run recorded (G4) | ⚪ untested: role file as prompt (G4) |
| Chief of Staff thread | 🟢 works | ⚪ untested (G2) | ⚪ untested (G3) | ⚪ untested (G18) |
| Ship loop child threads | 🟢 works | ⚪ untested (G2) | ⚪ untested (G3) | ⚪ untested (G18) |
| Stop hook (thread rotation) | 🟢 works | 🔴 not supported: hook installed for Claude Code and Cursor only (G7) | 🟡 partial: skill-change rotation only, no size trigger (G8) | 🔴 not supported: hook installed for Claude Code and Cursor only (G7) |
| Usage and cost report | 🟢 works | 🔴 not supported: reads Claude Code and Cursor runs only (G8) | 🟡 partial: models without a price show cost unknown (G8) | 🔴 not supported: reads Claude Code and Cursor runs only (G8) |
| Local dashboard | 🟢 works | 🟡 partial: no gantt rows or spend (G9) | 🟡 partial: no gantt rows or spend (G9); rest untested (G3) | 🟡 partial: no gantt rows or spend (G9); rest untested (G18) |
| `agent-gantt` | 🟡 partial: hooks run in T3 sessions, pane in T3 not seen (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) |
| `status-pane` | ⚪ untested: pane in T3 not seen (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) |
| Security review subagent | 🟢 works | ⚪ untested (G4) | ⚪ untested: role file as prompt (G4) | ⚪ untested: no Antigravity branch in the skill (G4) |

Notes:

- Install links each skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and `~/.cursor/skills`, and each subagent into `~/.claude/agents` and `~/.cursor/agents`. It writes the instruction block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. It writes the same text to `~/.cursor/rules/collective-wisdom.mdc` for Cursor, with `alwaysApply: true`. It writes nothing for Antigravity.
- `install.sh` adds the rotation Stop hook to `~/.claude/settings.json` and `~/.cursor/hooks.json`, and to no other harness. The Cursor hook has been tested only against Cursor's documented payload. It becomes `works` once a Cursor Chief of Staff thread has run it.
- The No Hands cost cap sums `agent_usage.py` over the run's tickets. A Cursor child is priced from its run store in `~/.cursor/projects`; a run on a model `prices.json` has no price for makes the ticket's cost unknown, and a No Hands run stops. A Codex or Antigravity child leaves nothing the script reads, so its cost is unknown and a No Hands run stops.
- Antigravity appears as a provider in T3 Code, and the repo has nothing for it yet.

### Full compatibility

One line per column, saying what done means.

- **Claude Code in T3 Code:** done. A Chief of Staff and its children run a ticket from spec to merge, with subagents, the rotation hook and cost figures. The two mods are the only open cells.
- **Codex in T3 Code:** done when a Chief of Staff and its children run a ticket to merge on Codex, with subagents, a rotation hook and cost figures that Codex can supply.
- **Cursor in T3 Code:** done when the instruction block installs without a manual paste, a Chief of Staff and its children run a ticket to merge on Cursor, with subagents, and the hook and cost figures work for it.
- **Antigravity in T3 Code:** done when `install.sh` installs skills and the instruction block for it, a Chief of Staff and its children run a ticket to merge on it, with subagents, a security review, a rotation hook and cost figures.

## Matrix 2: trackers

Columns are the ticket trackers the `Tracker` row in `docs/agents/project.md` can name (GitHub Issues, Linear and Jira), plus Azure DevOps, which it cannot name yet.

| Feature | GitHub Issues | Linear | Jira | Azure DevOps (ADO) |
|---|---|---|---|---|
| Ticket operations (the adapter) | 🟢 works | 🟢 works (see note) | ⚪ untested: adapter never run (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Chief of Staff and ship loop | 🟢 works | 🟢 works (see note) | ⚪ untested (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Project manager hygiene and ranking | 🟢 works | 🟢 works | 🔴 not supported: `pm_hygiene.py` has no Jira shape; ranking untested (G13) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Untracked work check | 🟢 works | 🟡 partial: finds open PRs only (G14) | 🟡 partial: finds open PRs only (G14) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Dashboard issue links, titles and update order | 🟢 works | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) |
| Setup (`set up this repo`) | 🟢 works | 🟢 works | ⚪ untested: writes the Jira rows, never run against Jira (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| PR flow and merge (needs GitHub for code) | 🟢 works | 🟢 works, code on GitHub | ⚪ untested, code on GitHub (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |

Notes:

- GitHub Issues: `trackers/github.md` says it was verified on 2026-11-03.
- Linear: `trackers/linear.md` has no verification line. Its `works` cells rest on the team running on Linear on one maintainer's machine, which is not a recorded verification; this covers every Linear `works` cell, not only the two marked. If you want `works` to mean a recorded verification like the GitHub adapter's, treat the Linear cells as `untested` (G16).
- Jira: `trackers/jira.md` is marked UNTESTED and its list of assumptions is unticked.
- Azure DevOps: here it means Azure Boards for tickets. The code stays on GitHub, as on every tracker. The repo has no mention of it outside an unrelated security checklist, so every cell is `not supported`.

### Full compatibility

- **GitHub Issues:** done. Every row works. The dashboard and the untracked check read issues, which only GitHub supports.
- **Linear:** done when the dashboard and the untracked check read Linear tickets as they read GitHub issues, and `trackers/linear.md` carries a verification line.
- **Jira:** done when the `jira.md` checklist is ticked against a live site, and `pm_hygiene.py` reads Jira's list shape.
- **Azure DevOps (ADO):** done when `trackers/` has an Azure DevOps adapter that the scripts read, verified against a live organization, and the dashboard and the untracked check read its work items.

## Keeping it current

A PR that changes support for a cell updates that cell in the same PR. When a cell goes from not `works` to `works`, drop its gap and its reason. A cell moves to `works` only with the code, or a run the team does today, to show it.

A gap ticket links back to its cell here, by row, column and gap number. When the ticket exists, put its link on the gap's line below, in place of `none yet`.

## Gaps

One line per gap the matrices point at. A ticket is opened only where the maintainer wants one, so each line says `none yet` until it exists.

- **G1.** `install.sh` writes the instruction block to `~/.cursor/rules/collective-wisdom.mdc`, but no Cursor thread in T3 Code is recorded reading it. Ticket: none yet.
- **G2.** No recorded Codex run in T3 Code: skills load, the Chief of Staff thread and the child threads are unchecked. Ticket: none yet.
- **G3.** No recorded Cursor run in T3 Code: skills load, the Chief of Staff thread and the child threads, and the dashboard's Chief of Staff state are unchecked. Ticket: none yet.
- **G4.** Subagents are proven only in Claude Code. Per Cursor's docs, Cursor loads Cursor-valid copies from `~/.cursor/agents`, but no Cursor run is recorded: the Cursor agent CLI was not logged in. Whether `readonly` also stops a reviewer's MCP write tools is unchecked. `AGENTS.md` says other hosts start a general subagent with the role file as its prompt, so Codex and Antigravity still work that way, and nobody has recorded doing it. The `security-review` skill has no Antigravity branch, so its security review runs the same way there. Ticket: none yet.
- **G5 and G6** are retired. Their numbers are not reused.
- **G7.** The rotation Stop hook is installed for Claude Code and Cursor only. Codex and Antigravity get no hook. Ticket: none yet.
- **G8.** `agent_usage.py` reads `~/.claude/projects` transcripts and Cursor's `~/.cursor/projects` run stores, so the cost report and the No Hands cost cap do not see Codex or Antigravity work, and a Cursor run on a model with no price in `prices.json` (such as `grok-4.7`) shows `cost unknown`. `--context` still reads Claude Code only, so a Cursor Chief of Staff has no context size and its rotation hook rotates only on a skill change. Ticket: none yet.
- **G9.** The dashboard's gantt rows and spend come from `agent-gantt` snapshots, which Codex, Cursor and Antigravity threads do not produce. Ticket: none yet.
- **G10.** `agent-gantt` and `status-pane` are Claude Code plugins, so Codex, Cursor and Antigravity threads do not run them, and whether T3 Code shows their panes for Claude Code is unchecked. Ticket: none yet.
- **G11** is resolved by CW-254. The `security-review` skill now has a Cursor child start a general subagent with `security-review.md` as its prompt, and ignore an installed `review-security` in the ship loop. No Cursor run is recorded yet (G4).
- **G12.** Jira has never been run: the adapter is marked UNTESTED and its checklist is unticked. Ticket: none yet.
- **G13.** `pm_hygiene.py` parses the Linear and GitHub list shapes, not Jira's. Ticket: none yet.
- **G14.** The untracked work check reads `agent`-labelled issues only for GitHub. On Linear and Jira it finds untracked work from open PRs alone. Ticket: none yet.
- **G15.** The dashboard's issue links, issue titles and update order call `gh issue` and are on only for GitHub. Ticket: none yet.
- **G16.** The Linear adapter has no verification line. Ticket: none yet.
- **G17.** `install.sh` writes nothing for Antigravity, neither skills nor the instruction block. Ticket: none yet.
- **G18.** No recorded Antigravity run in T3 Code: skills load, the Chief of Staff thread and the child threads, and the dashboard's Chief of Staff state are unchecked. Ticket: none yet.
- **G19.** There is no Azure DevOps adapter: `trackers/` has GitHub, Linear and Jira only, and the `Tracker` row in `project.md` cannot name it. Ticket: none yet.
