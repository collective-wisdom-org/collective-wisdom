# CW-219: Name gantt tasks by what the work is, not by the first line of the prompt

**Status:** Draft
**Ticket:** [#219](https://github.com/collective-wisdom-org/collective-wisdom/issues/219)
**Related:** CW-216 (waterfall by task, PR #218; fixed the preamble pattern), CW-191 (task chunks, where `taskName` came from).

## Goal

A task row on the gantt says what the work was: the ticket and what was being done on it. It never shows T3 Code's preamble or the wording of a Chief of Staff relay.

## Today

Facts from `main` at `73eefd9`.

- `taskName` in `mods/agent-gantt/hooks/timeline.ts` names a task when its prompt is submitted (`beginTask(r, taskName(e.text), since, t)` in the `prompt.submit` handler of `register.tsx`). It takes the first non-empty line that is not the whole-line preamble `PREAMBLE = /^Act as the .*agent for this task\.?$/i`, drops a leading `TEAM MODE.`, and cuts to 60 characters. The name is stored in the record and the snapshot; the prompt text is not.
- **Where the preamble rows came from.** The installed copy of the mod on this machine is `agent-gantt` 0.1.2 (`~/.claude/plugins/installed_plugins.json`, last updated 2026-11-08 00:33 UTC), from before CW-191. It has no `timeline.ts` and does not skip the preamble. The repo is at 0.1.5. All 26 snapshots under `.agent-team/gantt/` with an `Act as the ...` row were written by that copy. The current code skips `Act as the implementation sub-agent for this task.` when it is a line of its own (a `timeline.test.ts` case covers it). So a snapshot written by the current mod does not produce that row from the prompts T3 sends today.
- One gap remains in the current match: the preamble only counts as a whole line. A prompt with the preamble and the task on one line (`Act as the implementation sub-agent for this task. TEAM MODE. CONTINUE. Run /ship-loop. Do the build stage.`, the shape `test_agent_usage.py` uses) is named after the preamble.
- **Relay rows.** The Chief of Staff's relays are real first lines, so the current code names the task after them: `CHIEF OF STAFF: the user approved the spec: "approve 212". C…`. The relay shapes the team sends (`chief-of-staff/SKILL.md`, `continuation.md`):
  - `CHIEF OF STAFF: the user approved the spec: "<words>". Continue to the build stage.` and `CHIEF OF STAFF: auto-approved the spec ...`
  - `CHIEF OF STAFF: the user approved the merge of PR #X at head <sha>: "<words>".` and `CHIEF OF STAFF: auto-approved the merge of PR #X ...`
  - `CHIEF OF STAFF: the user asked for changes: "<words>".` and `CHIEF OF STAFF: a reviewer asked for changes on PR #N ...`
  - `CHIEF OF STAFF: continue the <stage> stage from where the branch is.` and `CHIEF OF STAFF: the user says: "<words>". Continue the <stage> stage.`
  - Others (`the user answered: ...`, `the spec at <sha> is not on GitHub ...`, `<the mismatch>. Fix it ...`).
  None of them names the ticket. The ticket is in the child's first prompt (`TEAM MODE. Run /ship-loop for CW-216: ...`), which is the name of an earlier task on the same `main` record.
- A continuation child's first line is `TEAM MODE. CONTINUE. Run /ship-loop for CW-N: <title>.`; today its name starts `CONTINUE. Run /ship-loop ...`.

## Design

`taskName(text, earlier)` takes the names of `main`'s earlier tasks as a second argument. `register.tsx` passes `r.tasks.map(k => k.name)`. The function stays pure.

1. **Preamble as a prefix.** `PREAMBLE` matches at the start of a line, not the whole line: `/^Act as the [\w -]*agent for this task\.?\s*/i`. It is stripped, and the rest of the line, if any, is used.
2. **Team markers.** After the preamble, a leading `TEAM MODE.` and then a leading `CONTINUE.` are dropped. `TEAM MODE. CONTINUE. Run /ship-loop for CW-9: fix` is named `Run /ship-loop for CW-9: fix`.
3. **Relays.** A line that starts `CHIEF OF STAFF:` is named `<ticket> <work>`:
   - `<ticket>` is the last ticket id (`[A-Z][A-Z0-9]*-\d+`) found in the earlier names, newest first. None found: no ticket, and the name is just `<work>`.
   - `<work>` comes from the first rule in this table that matches the relay (case-insensitive):

     | Relay contains | Work |
     |---|---|
     | `approved the spec` | `build` |
     | `approved the merge of PR #X` | `merge PR #X` |
     | `reviewer asked for changes on PR #N` | `changes on PR #N` |
     | `asked for changes` | `changes` |
     | `continue the <stage> stage` | `<stage>` |
     | anything else | the relay text after `CHIEF OF STAFF:` |

     So `CHIEF OF STAFF: the user approved the spec: "approve 216". Continue to the build stage.` after `Run /ship-loop for CW-216: Redesign the agent gantt` is named `CW-216 build`.
   - The table matches the relay's first line only, so words quoted from the user later in the prompt can't pick a row. A user's own words inside the first line's quotes can: `the user says: "approve the spec"` reads as `build`. That only changes a label.
4. Everything else is as today: whitespace collapsed, cut to 60 characters, `task` when no line is left.

A name that was fine stays the same: a prompt whose first real line has no marker gets exactly today's name.

**Rows written before the change** stay as they are. The prompt text is not stored, so there is nothing to re-derive a name from.

**Version.** `mods/agent-gantt/.claude-plugin/plugin.json` goes to 0.1.6 so `/plugin update` picks the change up. The PR says that this machine runs 0.1.2 and needs `/plugin update agent-gantt@collective-wisdom` (or a reinstall) to get CW-191, CW-216 and this change.

## Tests

One table-driven case added to the `taskName` test in `mods/agent-gantt/hooks/timeline.test.ts`, with rows for:

- the CW-216 implementation sub-agent prompt (preamble line, then `TEAM MODE. Run /ship-loop for CW-216: ...`), named by its run line;
- the preamble and task on one line;
- `TEAM MODE. CONTINUE. Run /ship-loop for CW-9: ...`;
- each relay row of the table, with earlier names that carry a ticket, and one with no ticket in the earlier names;
- the existing cases unchanged (names that were already fine).

## Leaves out

- Other prompts in the Chief of Staff's own thread that read badly: `CHIEF OF STAFF NOTICE: child thread:...`, `Delegated task node:...`, `TICKET HELPER. Chief of Staff thread: ...`, `CHIEF OF STAFF ROTATION from ...`. They are notices and helper launches, not the CW-216 shape, and naming them well is a different question (some may not be tasks at all). A follow-up ticket can take them.
- Row layout, bars, time and cost (CW-216).
- Changing the prompts the team sends.
- Rewriting names in snapshots already on disk.

## Calls I made

- **The preamble rows on the CW-216 card came from the stale installed mod (0.1.2), not from current code.** I fix only the one-line preamble gap in the match and say in the PR that the machine needs a plugin update.
- **A relay is named after the ticket from an earlier task on the same session**, not from the worktree path or branch: the relays don't name the ticket, the record's cwd is a T3 worktree path with no ticket in it, and the earlier task name already holds it. A session with no earlier ticket gets the work alone (`build`).
- **The relay table has five rows for the relay shapes the Chief of Staff sends.** Any other relay falls back to its own text without the `CHIEF OF STAFF:` marker. No other roles get special cases.
- **`TEAM MODE. CONTINUE.` drops `CONTINUE.`** too. That changes continuation children's names from `CONTINUE. Run /ship-loop ...` to `Run /ship-loop ...`.
- **The work words are short (`build`, `merge PR #218`, `changes`)**, not the stage names from state.
- **Old rows stay as they are**, since the prompt text is not stored.
- **The mod version goes to 0.1.6.**
