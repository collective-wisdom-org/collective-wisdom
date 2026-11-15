# CW-375: Stop naming a ticket helper after a ticket in its task text

**Status:** Shipped
**Shipped:** in PR #398, as specified
**Ticket:** [#375](https://github.com/collective-wisdom-org/collective-wisdom/issues/375)

## Goal

A ticket helper's row in the Agents panel reads `Ticket helper` until the helper files a ticket, then `Ticket helper <that ticket>`. It never takes an id from the prompt text.

## Today

Facts from main at `4b974cb`, all under `mods/agent-gantt/hooks/`.

- `taskName()` in `timeline.ts` names a task once, from its first prompt. For a `TICKET HELPER.` line it appends the first `<PREFIX>-N` anywhere in the prompt (`HELPERS` flag `true`), unless the line ends in `Observation.`. The context paragraph the Chief of Staff writes ahead of the request often names other tickets, so the row gets the wrong id.
- The name is stored on `main`'s task (`record.tasks[i].name`), and `buildRows()` in `rows.ts` copies it into the task row.
- The filed ticket is known later: T3 Code sets the `ticket` atom on `turn.complete` (`register.tsx`), Cursor sets `state.ticket` in `withFiledTicket()` (`cursor.ts`). Both use `pickFiledTicket()` and put the value in the snapshot's `ticket` field, which attaches the session to its ticket card.
- Rows are built in three places: the T3 Code snapshot (`writeSnapshot`), the T3 Code pane (`ui.render`), and the Cursor snapshot (`cursorSnapshot`). The dashboard Agents panel draws the snapshot rows.
- `timeline.test.ts` expects `Request: file a ticket for CW-12 and UTF-8` to give `Ticket helper CW-12`. That case pins the bug.

## Design

### `timeline.ts`

- `HELPERS` becomes `[marker, name]` pairs: no role takes an id from its prompt. A `TICKET HELPER.` line is named `Ticket helper`, with or without `Observation.`.

### `rows.ts`

- New pure function `withHelperTicket(rows, ticket)`: when `ticket` is a non-empty string, each `task` row named exactly `Ticket helper` is renamed `Ticket helper <ticket>`. Other rows, and every row when `ticket` is empty or null, come back unchanged.
- The constant `'Ticket helper'` is exported from `timeline.ts` (or shared) so the two files can't drift apart.

### Call sites

- `register.tsx`: the pane's `ui.render` passes its `buildRows()` result through `withHelperTicket(rows, await read($, ticket))`. `writeSnapshot` takes the ticket from the `ticket` atom, falling back to the old snapshot's `ticket` field, and uses that one value for both `withHelperTicket` and the snapshot's `ticket` field, so a resumed helper's label and card agree. The rows from an earlier process of the same session go through it too.
- `cursor.ts`: `cursorSnapshot` passes its rows through `withHelperTicket(rows, state.ticket)`.

The stored task name stays `Ticket helper`; the ticket is added at render. So the row updates on the next snapshot after the ticket is found, and a ticket that is never found (`Tickets: none`) leaves the plain name.

### Tests

- `timeline.test.ts`: the `CW-12` case now expects `Ticket helper`, and a new case has a prompt whose context paragraph names `CW-359` before the request marker; it gives `Ticket helper`.
- `rows.test.ts`: one table-driven test for `withHelperTicket`: ticket set renames the `Ticket helper` task row; null and empty leave it; an agent row and another task named `Ticket helper CW-1` or `Build CW-1: x` are left alone.
- `cursor.test.ts`: the existing ticket helper test checks the snapshot row name, `Ticket helper` before the stop and `Ticket helper CW-7` after it. That covers the Cursor wiring end to end. T3 Code's `register.tsx` has no test harness; its two call sites are one line each.

### Mod version

- Bump `mods/agent-gantt/.claude-plugin/plugin.json` from `0.1.12` to `0.1.13` (and the marketplace entry if it lists a version), so `claude plugin update` picks the change up.

## Files

| File | Change |
|---|---|
| `mods/agent-gantt/hooks/timeline.ts` | Drop the id from the helper name; export the helper name. |
| `mods/agent-gantt/hooks/rows.ts` | Add `withHelperTicket`. |
| `mods/agent-gantt/hooks/register.tsx` | Apply it in `writeSnapshot` and the pane. |
| `mods/agent-gantt/hooks/cursor.ts` | Apply it in `cursorSnapshot`. |
| `mods/agent-gantt/hooks/timeline.test.ts`, `rows.test.ts`, `cursor.test.ts` | Tests above. |
| `mods/agent-gantt/.claude-plugin/plugin.json` | Version bump. |

## Non-goals

- Names of other helper rows (`Backlog ranking`, `Hygiene`) and ship-loop rows.
- Which ticket card a helper session attaches to.
- Rewriting rows already saved in old snapshots: a past session named `Ticket helper CW-359` keeps that name, since only a row named exactly `Ticket helper` is renamed.

## Calls I made

- **The ticket is added when rows are built, not written into the stored task name.** One rule covers T3 Code and Cursor, needs no state migration, and works for sessions saved before this change once their ticket is known.
- **Old snapshots with a wrong name stay wrong.** Rows from a previous process that already say `Ticket helper CW-359` are not fixed; telling a buggy id from a real one would mean guessing.
- **Every `Ticket helper` task row in the session gets the ticket**, not only the first. A helper session normally has one task; a second prompt in the same helper session is still that helper's work.
- **The mod version is bumped to 0.1.13** so installed copies update. CW-359 changed hooks without a bump; this one changes what users see, so it bumps.
- **No dashboard page change.** The page draws the snapshot's row names as they come.
