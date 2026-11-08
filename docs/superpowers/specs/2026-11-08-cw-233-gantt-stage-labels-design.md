# CW-233: Label each gantt task row with its stage: Spec, Build or Merge

**Status:** Shipped
**Shipped:** in PR #237, as specified
**Ticket:** [#233](https://github.com/collective-wisdom-org/collective-wisdom/issues/233)
**Related:** CW-219 (task names, PR #221), CW-225 (own spans, PR #228), CW-227 (details section), CW-230 (page reload), CW-232 (bar tooltips).

## Goal

On a ticket card's Agents chart, each child thread's row says which stage it ran: `Spec CW-227: ...`, `Build CW-227: ...` or `Merge CW-227: ...`. The ticket helper, backlog ranking and hygiene children say their role. A reader tells the rows apart at a glance.

## Today

Facts from `main` at `d918a2b`.

- `taskName(text, earlier)` in `mods/agent-gantt/hooks/timeline.ts` names a task when its prompt is submitted (`register.tsx`, `prompt.submit`). It walks the prompt line by line, drops T3's preamble, a leading `TEAM MODE.` and then a leading `CONTINUE`, and returns the first non-empty line cut to 60 characters. A `CHIEF OF STAFF:` relay is named `<ticket> <work>` (CW-219). Only the name is stored; the prompt is not.
- The prompts the Chief of Staff sends:
  - First child (`chief-of-staff/SKILL.md` § Child task template): `TEAM MODE. Run /ship-loop for <PREFIX>-<N>: <title>. <ticket URL>.`
  - Continuation child (`chief-of-staff/continuation.md`): `TEAM MODE. CONTINUE. Run /ship-loop for <PREFIX>-<N>: <title>. <ticket URL>.`, and further down, on its own line, `Follow ship-loop. Do the <stage> stage (the lane's active stage), ...` with `<stage>` one of spec, build, merge.
  - Ticket helper (`chief-of-staff/ticket-helper.md`): first line `TICKET HELPER. Chief of Staff thread: <id>[ Request from <thread> item <item>.]`, or the same ending `Observation.`
  - Backlog ranking (`project-manager/reference.md`): first line `BACKLOG RANKING. One-shot, read only.`
  - Hygiene (`project-manager/reference.md`): first line `PROJECT MANAGER HYGIENE. One-shot.`
- After the markers go, the first child and every continuation child of a ticket are both named `Run /ship-loop for CW-227: ...`, and the helpers are named after the first line of their template.
- `agent_usage.py` reads the stage the same way: `TEAM MODE. CONTINUE` plus `Do the (spec|build|merge) stage` starts in that stage; any other first task starts in `spec`.
- The relay rule finds the ticket in `earlier` with `TICKET = /[A-Z][A-Z0-9]*-\d+/`. `Spec CW-227: ...` still contains `CW-227`, so relays keep working on the new names.

## Design

All in `taskName`. It stays pure, and `register.tsx` does not change.

1. **Ship-loop children.** When the first real line (after the preamble and the team markers) starts `Run /ship-loop for <ticket>:`, the name is `<Stage> <ticket>: <title>`, cut to 60 characters.
   - `<Stage>`: if the line had the `CONTINUE` marker, the stage from the first `Do the (spec|build|merge) stage` anywhere in the prompt, capitalized. With no `CONTINUE` marker, `Spec`.
   - A `CONTINUE` prompt with no `Do the <stage> stage` line keeps today's name (`Run /ship-loop for ...`): there is no stage to show, and guessing one would mislabel the row.
   - `<title>` is the rest of the line after `<ticket>:`, with a trailing ticket URL and its full stop dropped (` https://... .` at the end of the line). So `TEAM MODE. Run /ship-loop for CW-227: Add an expandable details section. https://github.com/o/r/issues/227.` becomes `Spec CW-227: Add an expandable details section`.
2. **Helper children.** When the first real line starts with one of these markers, the name is the role:

   | First line starts | Name |
   |---|---|
   | `TICKET HELPER.` | `Ticket helper` |
   | `BACKLOG RANKING.` | `Backlog ranking` |
   | `PROJECT MANAGER HYGIENE.` | `Hygiene` |

   If the prompt names a ticket id (the first `\b[A-Z][A-Z0-9]*-\d+\b` anywhere in it), it is added after the role: `Ticket helper CW-12`.
3. **Everything else** is as today, including relays, prompts with no marker and subagent rows (subagents are not named by `taskName`).

**Rows already stored** keep their names. The prompt is not stored, so there is nothing to re-derive from, and the dashboard does not re-derive on read. The PR says so. A machine on an older mod version keeps writing the old names until it updates.

**Version.** `mods/agent-gantt/.claude-plugin/plugin.json` goes from 0.1.7 to 0.1.8 so `/plugin update` picks the change up.

No change to `app.js`, the prompts the Chief of Staff sends, or subagent names.

## Tests

The cases go in the existing `taskName` table test in `mods/agent-gantt/hooks/timeline.test.ts`; the rows that today expect `Run /ship-loop for CW-9: fix` change to the new names. One new table for the stage and role rule, with rows for:

- a first child with the preamble and a ticket URL → `Spec CW-227: Add an expandable details section`
- a continuation child with `Do the build stage` on a later line → `Build CW-227: ...`, and one with `merge` → `Merge ...`
- a continuation child with no stage line → today's name
- a long title → cut to 60
- each of the three helper markers, one with a ticket id in the prompt
- a relay after a `Spec CW-216: ...` row → `CW-216 build` (relays still find the ticket)
- a plain prompt and a line that mentions `/ship-loop` mid-sentence → unchanged

`node --test mods/agent-gantt/hooks/*.test.ts` passes.

## Out of scope

- Bar tooltips (#232), the details section (#227), the page reload (#230), and `app.js` in general.
- Changing the prompts the Chief of Staff sends.
- Subagent row names.
- Renaming rows already stored.

## Calls I made

- **The ticket URL is dropped from the name.** The ticket asked to keep the 60-character cut, not the URL; with a short title the URL used to fill the rest of the row.
- **A `CONTINUE` prompt with no stage line keeps today's name** instead of guessing Build.
- **The stage is read anywhere in the prompt**, not just the first line, because `Do the <stage> stage` sits further down in the continuation template. The first match wins.
- **Helper ticket id: the first ticket-shaped id anywhere in the prompt.** The helper templates put no id on the first line; a request may name one in its task text. A word like `UTF-8` in the request would also match; that only changes a label.
- **Hygiene is named `Hygiene`**, the ticket's own example, not `Project manager hygiene`.
- **Only a line that starts `Run /ship-loop for <ticket>:`** gets a stage. A prompt that mentions `/ship-loop` some other way is left alone.
- **Mod version bump to 0.1.8**, as CW-219 did, so installed copies can update.
