# CW-223: A compatibility document for harnesses and trackers

**Status:** Draft
**Ticket:** [#223](https://github.com/collective-wisdom-org/collective-wisdom/issues/223)

## Goal

One page that says which team features work on which harness and which ticket tracker, so a person adopting the team knows what to expect and every gap has a place to point a ticket at. Today these facts are spread over `README.md`, `AGENTS.md`, `install.sh`, the scripts and the adapter docs.

## What I checked

Facts from `main` at `5b800cd`, and from this machine on 2026-11-08.

- **Install.** `install.sh` links each skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and `~/.cursor/skills`, and each subagent into `~/.claude/agents` only. It writes the instruction block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. Cursor gets the block as a `TODO:` to paste into its user rules by hand.
- **Stop hook.** `install.sh` adds the `cos_rotation_check.py --hook` Stop hook to `~/.claude/settings.json` only. Nothing installs a hook for Codex or Cursor.
- **Subagents.** `agent-team/.claude/agents/*.md` load only in Claude Code. `AGENTS.md` says other hosts start a general subagent with the role file as its prompt; nobody has recorded doing that.
- **T3 Code.** `README.md` § Requirements lists T3 Code for the Chief of Staff and child threads. The chief-of-staff, project-manager and ship-loop skills call T3 thread tools (`t3_thread_read`, `t3_background_wait` and others). The local dashboard opens in the T3 browser pane.
- **Usage and cost.** `agent_usage.py` reads `~/.claude/projects` transcripts only. The No Hands cost cap and the dashboard cost figures depend on it or on the `agent-gantt` rows, which are Claude Code hook events.
- **Mods.** `agent-gantt` (`mods/agent-gantt/`) and `status-pane` are Claude Code plugins.
- **Security review.** The `security-review` skill names Claude Code's `security-reviewer` subagent and Cursor's `review-security` skill, which this repo does not ship.
- **Trackers.** `trackers/github.md` says **Verified** 2026-11-03. `trackers/linear.md` has no verification line, but fathom on this machine runs the team with `Tracker` set to `linear`. `trackers/jira.md` says **UNTESTED** and has an unchecked list of assumptions.
- **GitHub-only code.** `cos_untracked_check.py` reads `agent`-labelled issues only when the tracker is `github`; on other trackers it finds untracked work from PRs alone. The dashboard's issue links, issue titles and "by last update" order call `gh issue` and are on only for `github`. `pm_hygiene.py` parses the Linear and GitHub list shapes, not Jira's.
- **GitHub for code.** `merge_pr.py`, `wait-for-ci.sh`, `review_gate.py` and the PR flow call `gh.sh` whatever the tracker is, so every tracker needs the code on GitHub.

## Builds

1. **`docs/compatibility.md`**, at the repo root's `docs/`, beside `docs/agents/` and `docs/superpowers/`. It is this repo's doc, not shipped to apps.
2. **Cell values.** One legend: `works`, `partial`, `not supported`, `untested`. A cell that is not `works` carries a short reason and a ticket link or `none yet`. A cell is `works` only where the code or a recorded run shows it; otherwise `untested`.
3. **Matrix 1, harnesses.** Columns:
   - Claude Code in T3 Code
   - Codex in T3 Code
   - Claude Code alone (terminal or desktop app, no T3)
   - Codex alone
   - Cursor

   Rows: install (skills and instruction block), team skills load, subagents, Chief of Staff thread, ship loop child threads, ship loop by hand, Stop hook (thread rotation), usage and cost report (`agent_usage.py`, No Hands cost cap), local dashboard, `agent-gantt`, `status-pane`, security review subagent.
4. **Matrix 2, trackers.** Columns GitHub Issues, Linear, Jira. Rows: ticket operations (the adapter), Chief of Staff and ship loop, project manager hygiene and ranking, untracked work check, dashboard issue links, titles and update order, setup (`set up this repo`), PR flow and merge (needs GitHub for code).
5. **Full compatibility line** under each matrix, one line per column, saying what done means. For example: Codex in T3 Code is done when a Chief of Staff and its children run a ticket to merge, with subagents, the rotation hook and cost figures. Jira is done when the `jira.md` checklist is ticked against a live site and `pm_hygiene.py` reads its shape.
6. **Keeping it current.** A short section: a PR that changes support for a cell updates that cell in the same PR, and a gap ticket links back to its cell.
7. **Gap list.** A section listing each gap the matrices point at, one line each, with `none yet` until a ticket exists. This PR opens no tickets.
8. **README link.** One line in `README.md` § Requirements (or beside Choosing a tracker) pointing at `docs/compatibility.md`.

## Seed values (the build checks each against the code again)

Harnesses (CC = Claude Code):

| Feature | CC in T3 | Codex in T3 | CC alone | Codex alone | Cursor |
|---|---|---|---|---|---|
| Install | works | works | works | works | partial: rules pasted by hand |
| Team skills load | works | untested | works | untested | untested |
| Subagents | works | untested: role file as prompt | works | untested | untested |
| Chief of Staff thread | works | untested | not supported: needs T3 | not supported | not supported |
| Ship loop child threads | works | untested | not supported | not supported | not supported |
| Ship loop by hand | works | untested | partial: `t3_background_wait` missing | untested | untested |
| Stop hook | works | not supported | works (only matters for a Chief of Staff) | not supported | not supported |
| Usage and cost | works | not supported | works | not supported | not supported |
| Local dashboard | works | partial: no gantt rows | not supported: T3 pane | not supported | not supported |
| agent-gantt | untested in T3 | not supported | works | not supported | not supported |
| status-pane | untested in T3 | not supported | works | not supported | not supported |
| Security review subagent | works | untested | works | untested | partial: needs Cursor's own `review-security` |

Trackers:

| Feature | GitHub Issues | Linear | Jira |
|---|---|---|---|
| Ticket operations | works | works | untested |
| Chief of Staff and ship loop | works | works | untested |
| Project manager hygiene and ranking | works | works | not supported: `pm_hygiene.py` has no Jira shape |
| Untracked work check | works | partial: PRs only | partial: PRs only |
| Dashboard issue links, titles, order | works | not supported | not supported |
| Setup | works | works | untested |
| PR flow and merge | works | works, code on GitHub | untested, code on GitHub |

## Leaves out

- Making any gap work, and opening the gap tickets. Each gap is its own ticket, opened only where you want it.
- Testing Linear or Jira against a live account, or running Codex or Cursor to confirm a cell.
- Code hosts other than GitHub (GitLab and the like): one line says the team needs GitHub for code, nothing more.
- Tests: the doc is prose, and `AGENTS.md` § Testing says not to test prose.

## Testing

`python3 -I -m pytest -q agent-team/scripts` still passes (no script changes). The build spot-checks each cell against `install.sh`, `agent_usage.py`, `cos_untracked_check.py`, `pm_hygiene.py`, the dashboard and `trackers/*.md`.

## Calls I made

- **Linear counts as `works`, not `untested`.** Its adapter has no verification line, but fathom runs the team on Linear on this machine. If you want `works` to mean a recorded verification like `github.md`'s, Linear drops to `untested` across the board.
- **Five harness columns, not four.** The ticket says "Claude Code, Codex, Cursor and T3 Code on each". I read that as Claude Code and Codex each with and without T3 Code, plus Cursor. I left out Cursor in T3 Code because nothing here shows T3 runs Cursor.
- **No gap tickets opened.** Every non-`works` cell says `none yet`, and the gap list shows what each ticket would be. Tell me which to open as Backlog tickets.
- **Codex in T3 Code is mostly `untested`, not `not supported`.** The skills and instruction block reach Codex, but nobody has recorded a Codex run. The cells that need Claude Code-only pieces (hook, transcripts, mods) are `not supported`.
- **The doc lives at `docs/compatibility.md`**, as the ticket assumed. It is about this repo's product, so it stays out of `agent-team/` and is not shipped to apps.
- **Claude Code in T3 Code for the two mods is `untested`.** T3 Code may not show a Claude Code plugin pane; I have not checked.
