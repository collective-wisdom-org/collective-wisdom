# CW-375 plan: ticket helper row label

Spec: `docs/superpowers/specs/2026-11-14-cw-375-helper-label-design.md`. All paths under `mods/agent-gantt/`.

Test command: `node --test hooks/*.test.ts` run from `mods/agent-gantt`, plus the full command in `docs/agents/project.md` and the dashboard node tests from `AGENTS.md`.

## Task 1: names and rename function

1. `hooks/timeline.ts`: drop the boolean from `HELPERS`; `TICKET HELPER.` always gives `Ticket helper`. Export `TICKET_HELPER = 'Ticket helper'` and use it in `HELPERS`.
2. `hooks/rows.ts`: add `withHelperTicket(rows, ticket)` per the spec (task rows named exactly `Ticket helper`, non-empty ticket only).
3. `hooks/timeline.test.ts`: the `CW-12` case expects `Ticket helper`; add a case with `CW-359` in a context paragraph before the request marker. `hooks/rows.test.ts`: one table test for `withHelperTicket`.

## Task 2: wire the call sites

1. `hooks/register.tsx`: pass `writeSnapshot` rows (earlier + built) and the pane rows through `withHelperTicket` with the `ticket` atom value.
2. `hooks/cursor.ts`: `cursorSnapshot` passes its rows through `withHelperTicket(rows, state.ticket)`.
3. `hooks/cursor.test.ts`: the existing ticket helper test also checks the task row name before (`Ticket helper`) and after (`Ticket helper CW-7`) the stop.

## Task 3: version

Bump `.claude-plugin/plugin.json` to `0.1.13`.
