# CW-226: Harness matrix with T3 Code columns only

**Status:** Shipped
**Shipped:** in PR #229, as specified
**Ticket:** [#226](https://github.com/collective-wisdom-org/collective-wisdom/issues/226)

## Goal

The team is built for T3 Code, so the harness matrix in `docs/compatibility.md` should only list T3 Code running each harness. Drop the standalone columns, and add Cursor and Antigravity in T3 Code so a person on either knows what to expect.

## What I checked

Facts from `main` at `2b72502`.

- `docs/compatibility.md` § Matrix 1 has five columns: Claude Code in T3 Code, Codex in T3 Code, Claude Code alone, Codex alone, Cursor. The matrix intro says Cursor in T3 Code is not a column.
- Gaps used only by the standalone columns: `G5` (Chief of Staff, dashboard and `status-pane` need T3 Code) and `G6` (CI wait needs `t3_background_wait`). The "Ship loop by hand" row exists to describe sessions without T3 Code.
- `install.sh` links skills into `~/.claude/skills`, `~/.agents/skills` and `~/.cursor/skills`, subagents into `~/.claude/agents` only, and prints the instruction block for a manual paste into Cursor's user rules. It adds the Stop hook to `~/.claude/settings.json` only.
- Antigravity is not mentioned anywhere in the repo. `install.sh` writes nothing for it.
- The `security-review` skill has a Cursor branch (`review-security`) and a Claude Code branch, and none for Antigravity.
- `agent_usage.py` reads `~/.claude/projects` only. `agent-gantt` and `status-pane` are Claude Code plugins.
- Matrix 2 cells use `G12` to `G16`.

## Builds

Only `docs/compatibility.md` changes.

1. **Columns.** Matrix 1 becomes: Claude Code in T3 Code, Codex in T3 Code, Cursor in T3 Code, Antigravity in T3 Code. The three standalone columns go.
2. **Rows.** Drop "Ship loop by hand". In T3 Code a ticket runs through the Chief of Staff and child threads, which already have rows. The other eleven rows stay.
3. **Claude Code and Codex cells** stay as they are, except the Codex cells that pointed at `G2` keep `G2` with its reworded text (below).
4. **New cells**, seeded from the repo, never `works`:

   | Feature | Cursor in T3 Code | Antigravity in T3 Code |
   |---|---|---|
   | Install (skills and instruction block) | partial: rules pasted by hand (G1) | not supported: `install.sh` writes nothing for it (G17) |
   | Team skills load | untested (G3) | untested (G18) |
   | Subagents | untested: role file as prompt (G4) | untested: role file as prompt (G4) |
   | Chief of Staff thread | untested (G3) | untested (G18) |
   | Ship loop child threads | untested (G3) | untested (G18) |
   | Stop hook (thread rotation) | not supported: hook installed for Claude Code only (G7) | same (G7) |
   | Usage and cost report | not supported: reads Claude Code transcripts only (G8) | same (G8) |
   | Local dashboard | partial: no gantt rows or spend (G9); rest untested (G3) | partial: no gantt rows or spend (G9); rest untested (G18) |
   | `agent-gantt` | not supported: Claude Code plugin (G10) | same (G10) |
   | `status-pane` | not supported: Claude Code plugin (G10) | same (G10) |
   | Security review subagent | partial: needs Cursor's own `review-security` (G11) | untested: no Antigravity branch in the skill (G4) |

   In the page each "same" is written out in full.

5. **Gaps.**
   - Retire `G5` and `G6`: no cell uses them once the standalone columns go. Their numbers are not reused, and a line under § Gaps says so.
   - Keep the other numbers, so Matrix 2's `G12` to `G16` and the Codex cells do not change.
   - Reword `G2` to drop "alone" and "the ship loop by hand": no recorded Codex run in T3 Code for skills load and the Chief of Staff and child threads.
   - Reword `G3` to Cursor in T3 Code: skills load, the Chief of Staff and child threads, and the dashboard's Chief of Staff state are unchecked.
   - Reword `G4`, `G7`, `G8`, `G9` and `G10` to name every harness other than Claude Code (Codex, Cursor and Antigravity), where they name Codex or Cursor today.
   - Add `G17`: `install.sh` writes nothing for Antigravity, neither skills nor the instruction block. Ticket: none yet.
   - Add `G18`: no recorded Antigravity run in T3 Code: skills load, the Chief of Staff and child threads, and the dashboard's Chief of Staff state are unchecked. Ticket: none yet.
6. **Intro and notes.**
   - The matrix intro says each column is a T3 Code thread running that harness, and that the team is built for T3 Code, so sessions without it are not covered. It drops the sentence about Cursor in T3 Code not being a column.
   - The No Hands note names Codex, Cursor and Antigravity children.
   - Add a note: Antigravity appears as a provider in T3 Code, and the repo has nothing for it yet.
7. **Full compatibility.** One line per new column; the Claude Code alone, Codex alone and Cursor lines go. Claude Code and Codex lines stay as they are. Cursor in T3 Code: done when the instruction block installs without a manual paste, a Chief of Staff and its children run a ticket to merge on Cursor, with subagents and `review-security`, and the hook and cost figures work for it. Antigravity in T3 Code: done when `install.sh` installs skills and the instruction block for it, a Chief of Staff and its children run a ticket to merge on it, with subagents, a security review, a rotation hook and cost figures.
8. **README.** Its link text ("What works on which harness and tracker") names no column, so it stays.

## Leaves out

- Matrix 2 and its notes.
- Making any gap work, including Antigravity support in `install.sh`.
- Running Cursor or Antigravity to check cells.
- Opening gap tickets.

## Calls I made

- **Retired `G5` and `G6` instead of renumbering.** Renumbering would change the gap numbers in Matrix 2's cells, and the ticket says Matrix 2 stays as it is. New gaps take `G17` and `G18`.
- **Dropped the "Ship loop by hand" row.** The ticket names it as existing only because of the standalone columns. A by-hand run inside T3 Code is not listed separately.
- **Antigravity install is `not supported`, not `untested`.** `install.sh` shows it writes nothing for Antigravity, so the code settles it.
- **Antigravity skills load is `untested`, not `not supported`.** Nothing in the repo says where Antigravity reads skills, so it may or may not pick up `~/.agents/skills`.
- **Antigravity security review points at `G4`** (role file as a general subagent prompt), since the skill has no Antigravity branch, rather than a new gap.
- **Local dashboard on Cursor and Antigravity is `partial`.** The gantt rows and spend are Claude Code only (code shows it); the Chief of Staff state part is untested.
- **Cursor in T3 Code is taken as a real setup**, as the ticket asks, even though nothing in the repo shows T3 Code running Cursor. Every Cursor cell that needs T3 Code is `untested`.
