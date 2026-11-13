# CW-290: Add ticket helper support in the agent gantt to the compatibility doc

**Status:** Shipped
**Shipped:** in PR #294, as specified
**Ticket:** [#290](https://github.com/collective-wisdom-org/collective-wisdom/issues/290)
**Related:** [#286](https://github.com/collective-wisdom-org/collective-wisdom/issues/286) (PR [#289](https://github.com/collective-wisdom-org/collective-wisdom/pull/289)), [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288)

## Goal

`docs/compatibility.md` says, for each harness column, what a ticket helper gets in the agent gantt: a placeholder card while it runs, its session attached to the ticket it filed, and its time and cost in that ticket's gantt and spend. Every claim matches the code merged by #286.

## Today

Facts from `main` at `34031d8` and from PR #289's branch `feat/cw-286-helpers-on-ship-loop` at `4975b2e`. The build re-checks each fact against `main` after #289 merges and fixes the doc to the merged code if anything moved.

- `docs/compatibility.md` says nothing about ticket helpers. Matrix 1 has `Local dashboard` and `agent-gantt` rows; G9 covers Cursor snapshot timing, models, tokens and cost; G10 says `agent-gantt` is a Claude Code plugin.
- #286, Claude Code: `mods/agent-gantt/hooks/register.tsx` sets `request` from the task prompt (`pickRequest`) and `ticket` from the main loop's final answer (`pickFiledTicket`, the first `<PREFIX>-N` under `Tickets:` in the `TICKET HELPER DONE` block), both only when the heading is `TICKET HELPER`. `buildSnapshot` in `snapshot.ts` writes both into the snapshot. The plugin version goes to `0.1.11`, so a machine gets this only after it updates the plugin.
- #286, dashboard (`agent-team/scripts/dashboard/api.ts`):
  - `cleanTeamSnapshot` keeps `ticket` only when it matches `^<prefix>-\d+$`.
  - `buildApi` puts a running helper (heading `TICKET HELPER`, no `ticket`, main turn open, and either a Cursor snapshot or updated in the last 60 seconds) in a `Writing tickets` group as a placeholder card. A finished helper with no ticket shows nowhere.
  - A helper session with a `ticket` joins that ticket's row gantt, live from the snapshot and finished from the history.
  - `ledgerSessions` puts a root checkout helper session with a `ticket` in that ticket's spend ledger, so its time and cost count in the ticket's spend (`server.ts` records it and the history).
- Cursor: `mods/agent-gantt/hooks/cursor.ts` sets `heading` with `pickHeading`, so a Cursor helper's snapshot has heading `TICKET HELPER`, but `cursorSnapshot` passes no `ticket` or `request` to `buildSnapshot`. So a running Cursor helper is a placeholder card with an empty title, it stays a card for the rest of its turn after it files, and it never joins the ticket or its spend. [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288) (CW-288) covers this and is not built. No Cursor hook run is recorded (G9).
- Codex and Antigravity threads write no gantt snapshot (G9), so their helpers show nowhere.

## Design

Docs only: `docs/compatibility.md`.

1. **New Matrix 1 row** `Ticket helper in the gantt`, after `agent-gantt`:
   - Claude Code: `🟢 works` (the #286 code shows the card, the attach and the spend). A note says it needs the `agent-gantt` plugin at `0.1.11` or later.
   - Codex: `🔴 not supported: no gantt snapshot (G9)`.
   - Cursor: `🟡 partial: placeholder card while it runs, not attached to the ticket it files, so its time and cost miss that ticket's gantt and spend (G21)`. Partial, not works, because the card rests on code with no recorded Cursor hook run (G9).
   - Antigravity: `🔴 not supported: no gantt snapshot (G9)`.
2. **New gap G21**: the Cursor gantt hook writes no `ticket` or `request`, so a Cursor helper's card has no title, stays until its turn ends, and its session never joins the ticket it filed. Ticket: [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288).
3. **One Matrix 1 note** on how a helper attaches: the mod reads the ticket from the `TICKET HELPER DONE` block of a Claude Code helper's final answer, and the dashboard adds that session to the ticket's gantt and spend; a finished helper that filed nothing leaves no card.
4. **Full compatibility** for Claude Code: the sentence "The two mods are the only open cells" stays true (the new row is `works`). No other line changes.
5. **Last checked** line: dated the build day, naming the #286 merge.

## Leaves out

- Building any support: Cursor is #288; Codex and Antigravity have no ticket.
- Other helper roles (Backlog ranking, hygiene) in the gantt.
- The Ship loop tab's new `Not started` band from #286.

## Calls I made

- A new Matrix 1 row and a new gap G21, rather than a note under the matrix or a line in G9: a row puts each harness's answer in its own cell, which the doc's legend rules are built for, and a gap gives the Cursor cell a ticket link.
- Cursor is `partial`, not `not supported`: the placeholder card comes from code that already runs for Cursor snapshots. It is not `works` because no Cursor hook run is recorded.
- Codex and Antigravity point at the existing G9 (no snapshot), not a new gap, since the cause is the same and the ticket says they have no ticket.
- Claude Code is `works` on the code alone, as the legend allows; no live helper run is recorded (PR #289 lists that under Not proven).
- The note names plugin version `0.1.11`, because an older installed plugin writes no `ticket`.

## Acceptance

- `docs/compatibility.md` states, per harness, what a ticket helper gets in the agent gantt, and every claim matches `main` after #289 merges.
- A cell is `works` only where the code shows it.
- `python3 -I -m pytest -q agent-team/scripts` passes.
