# Compatibility

What the agent team does on each harness and each ticket tracker, and where it does not. Read this before you adopt the team on a setup other than Claude Code in T3 Code with GitHub Issues. It is this repo's own page and is not shipped to apps.

Last checked against the code on 2026-11-08.

## Legend

| Value | Meaning |
|---|---|
| works | The code shows it, or someone has run it and recorded it |
| partial | Part of it works. The cell says what does not |
| not supported | Nothing here makes it work on this column |
| untested | Nothing shows it either way. Nobody has recorded a run |

A cell is `works` only where the code or a recorded run shows it. Anything else is `untested`.

A cell that is not `works` gives a short reason and a gap number such as `G3`. The [Gaps](#gaps) list holds one line per gap with its ticket link, or `none yet` while there is no ticket.

The team needs GitHub for code on every tracker. The PR flow, the merge gate and the CI wait call `~/.collective-wisdom/scripts/gh.sh` whatever the tracker is. Other code hosts are out of scope.

## Matrix 1: harnesses

Columns are the places a person runs an agent session. "In T3 Code" means a thread in T3 Code running that harness. "Alone" means a terminal or desktop app with no T3 Code. Cursor in T3 Code is not a column, because nothing here shows T3 Code running Cursor.

| Feature | Claude Code in T3 Code | Codex in T3 Code | Claude Code alone | Codex alone | Cursor |
|---|---|---|---|---|---|
| Install (skills and instruction block) | works | works | works | works | partial: rules pasted by hand (G1) |
| Team skills load | works | untested (G2) | works | untested (G2) | untested (G3) |
| Subagents | works | untested: role file as prompt (G4) | works | untested: role file as prompt (G4) | untested: role file as prompt (G4) |
| Chief of Staff thread | works | untested (G2) | not supported: needs T3 (G5) | not supported: needs T3 (G5) | not supported: needs T3 (G5) |
| Ship loop child threads | works | untested (G2) | not supported: needs T3 (G5) | not supported: needs T3 (G5) | not supported: needs T3 (G5) |
| Ship loop by hand | works | untested (G2) | partial: CI wait needs `t3_background_wait` (G6) | untested (G2) | untested (G3) |
| Stop hook (thread rotation) | works | not supported: hook installed for Claude Code only (G7) | works, but only a Chief of Staff needs it | not supported: hook installed for Claude Code only (G7) | not supported: hook installed for Claude Code only (G7) |
| Usage and cost report | works | not supported: reads Claude Code transcripts only (G8) | works | not supported: reads Claude Code transcripts only (G8) | not supported: reads Claude Code transcripts only (G8) |
| Local dashboard | works | partial: no gantt rows or spend (G9) | not supported: shows Chief of Staff state, which needs T3 (G5) | not supported: shows Chief of Staff state, which needs T3 (G5) | not supported: shows Chief of Staff state, which needs T3 (G5) |
| `agent-gantt` | untested: hooks read T3 sessions, pane in T3 not seen (G10) | not supported: Claude Code plugin (G10) | works | not supported: Claude Code plugin (G10) | not supported: Claude Code plugin (G10) |
| `status-pane` | untested: pane in T3 not seen (G10) | not supported: Claude Code plugin (G10) | partial: ticket groups come from Chief of Staff state, which needs T3 (G5) | not supported: Claude Code plugin (G10) | not supported: Claude Code plugin (G10) |
| Security review subagent | works | untested (G4) | works | untested (G4) | partial: needs Cursor's own `review-security` (G11) |

Notes:

- Install links each skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and `~/.cursor/skills`, and each subagent into `~/.claude/agents` only. It writes the instruction block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. Cursor has no file to write, so `install.sh` prints the block for you to paste into Cursor's user rules.
- `install.sh` adds the rotation Stop hook to `~/.claude/settings.json` only.
- The No Hands cost cap sums `agent_usage.py` over the run's tickets. A Codex or Cursor child leaves no Claude Code transcript, so its cost is unknown and a No Hands run stops.

### Full compatibility

One line per column, saying what done means.

- **Claude Code in T3 Code:** done. A Chief of Staff and its children run a ticket from spec to merge, with subagents, the rotation hook and cost figures. The two mods are the only open cells.
- **Codex in T3 Code:** done when a Chief of Staff and its children run a ticket to merge on Codex, with subagents, a rotation hook and cost figures that Codex can supply.
- **Claude Code alone:** done when the ship loop runs a ticket by hand from spec to merge, including the CI wait, without T3 Code. Running a Chief of Staff needs T3 Code and is not part of this column.
- **Codex alone:** done when the ship loop runs a ticket by hand from spec to merge on Codex, with subagents.
- **Cursor:** done when the instruction block installs without a manual paste, and the ship loop runs a ticket by hand from spec to merge with `review-security`.

## Matrix 2: trackers

Columns are the ticket trackers the `Tracker` row in `docs/agents/project.md` can name.

| Feature | GitHub Issues | Linear | Jira |
|---|---|---|---|
| Ticket operations (the adapter) | works | works (see note) | untested: adapter never run (G12) |
| Chief of Staff and ship loop | works | works (see note) | untested (G12) |
| Project manager hygiene and ranking | works | works | not supported: `pm_hygiene.py` has no Jira shape; ranking untested (G13) |
| Untracked work check | works | partial: finds open PRs only (G14) | partial: finds open PRs only (G14) |
| Dashboard issue links, titles and update order | works | not supported: GitHub only (G15) | not supported: GitHub only (G15) |
| Setup (`set up this repo`) | works | works | untested: writes the Jira rows, never run against Jira (G12) |
| PR flow and merge (needs GitHub for code) | works | works, code on GitHub | untested, code on GitHub (G12) |

Notes:

- GitHub Issues: `trackers/github.md` says it was verified on 2026-11-03.
- Linear: `trackers/linear.md` has no verification line. The cells say `works` because the team runs on Linear on one maintainer's machine, which is not a recorded verification. If you want `works` to mean a recorded verification like the GitHub adapter's, treat the Linear cells as `untested` (G16).
- Jira: `trackers/jira.md` is marked UNTESTED and its list of assumptions is unticked.

### Full compatibility

- **GitHub Issues:** done. Every row works. The dashboard and the untracked check read issues, which only GitHub supports.
- **Linear:** done when the dashboard and the untracked check read Linear tickets as they read GitHub issues, and `trackers/linear.md` carries a verification line.
- **Jira:** done when the `jira.md` checklist is ticked against a live site, and `pm_hygiene.py` reads Jira's list shape.

## Keeping it current

A PR that changes support for a cell updates that cell in the same PR. When a cell goes from not `works` to `works`, drop its gap and its reason. A cell moves to `works` only with the code or a recorded run to show it.

A gap ticket links back to its cell here, by row, column and gap number. When the ticket exists, put its link on the gap's line below, in place of `none yet`.

## Gaps

One line per gap the matrices point at. A ticket is opened only where the maintainer wants one, so each line says `none yet` until it exists.

- **G1.** Cursor has no file for user rules, so the instruction block is pasted by hand. Ticket: none yet.
- **G2.** No recorded Codex run: skills load, the Chief of Staff thread, child threads and the ship loop by hand are unchecked on Codex, in T3 Code and alone. Ticket: none yet.
- **G3.** No recorded Cursor run: skills load and the ship loop by hand are unchecked on Cursor. Ticket: none yet.
- **G4.** Subagents load only in Claude Code. `AGENTS.md` says other hosts start a general subagent with the role file as its prompt, and nobody has recorded doing it. Ticket: none yet.
- **G5.** The Chief of Staff and the child threads call T3 Code's thread tools, and the dashboard and `status-pane` show the Chief of Staff's state. Nothing replaces them outside T3 Code. Ticket: none yet.
- **G6.** The ship loop's CI wait calls `t3_background_wait`, which Claude Code alone does not have. Ticket: none yet.
- **G7.** The rotation Stop hook is installed for Claude Code only. Codex and Cursor get no hook. Ticket: none yet.
- **G8.** `agent_usage.py` reads `~/.claude/projects` transcripts only, so the cost report and the No Hands cost cap do not see Codex or Cursor work. Ticket: none yet.
- **G9.** The dashboard's gantt rows and spend come from `agent-gantt` snapshots, which Codex threads do not produce. Ticket: none yet.
- **G10.** `agent-gantt` and `status-pane` are Claude Code plugins, and whether T3 Code shows their panes is unchecked. Ticket: none yet.
- **G11.** The security review skill names Cursor's `review-security`, which this repo does not ship. Ticket: none yet.
- **G12.** Jira has never been run: the adapter is marked UNTESTED and its checklist is unticked. Ticket: none yet.
- **G13.** `pm_hygiene.py` parses the Linear and GitHub list shapes, not Jira's. Ticket: none yet.
- **G14.** The untracked work check reads `agent`-labelled issues only for GitHub. On Linear and Jira it finds untracked work from open PRs alone. Ticket: none yet.
- **G15.** The dashboard's issue links, issue titles and update order call `gh issue` and are on only for GitHub. Ticket: none yet.
- **G16.** The Linear adapter has no verification line. Ticket: none yet.
