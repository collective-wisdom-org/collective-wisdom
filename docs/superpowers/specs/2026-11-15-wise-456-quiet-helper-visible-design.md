# WISE-456: Keep a quiet ticket helper in Writing tickets until its thread finishes

**Status:** Shipped
**Ticket:** [#456](https://github.com/collective-wisdom-org/collective-wisdom/issues/456)
**Shipped:** in PR #458, as specified

## Goal

A ticket helper that works on its own for more than a minute, with no subagent, drops out of the Backlog tab's Writing tickets group while its thread is still running. It should stay there until its turn ends, with an upper bound so a crashed helper does not show forever.

## Today

Facts from main at `47f894f`.

- `buildApi` in `agent-team/scripts/dashboard/api.ts` builds the Writing tickets group from team items with role `helper`, no filed ticket, and `isRunning(i)`, where `isRunning = i.open && (i.cursor === true || now - i.session.updatedAt <= RUNNING_MS)` and `RUNNING_MS` is `60_000`.
- `open` (from `cleanWith`) is true while the snapshot's `main` row or one of its `main:task:N` rows has an open last segment, meaning a main-loop turn is in progress.
- The Claude Code mod (`mods/agent-gantt/hooks/register.tsx`) writes the snapshot from `refresh`, which runs on hook events. Its 5 second tick runs only while a non-main row is open (a subagent). A helper doing its own work has no tick, so `updatedAt` stops moving between events, and after 60 seconds the helper is hidden.
- A helper that finishes gets `turn.complete`, which closes `main` and rewrites the file, so `open` is false and the helper is hidden at once.
- The same `isRunning` decides the chief's `running` state and each project manager row's `running` or `finished`.

## Design

### 1. A longer window for helpers only, in the dashboard

Add `const HELPER_RUNNING_MS = 30 * 60_000` beside `RUNNING_MS` in `api.ts`, and use it for the Writing tickets filter:

```ts
const helperRunning = (i: TeamItem) => i.open && (i.cursor === true || now - i.session.updatedAt <= HELPER_RUNNING_MS)
```

- An open helper stays in Writing tickets for up to 30 minutes after its last snapshot write. Any hook event (a tool wait, a prompt, a subagent) rewrites the file and restarts the window.
- A finished helper is still hidden at once: its `main` row is closed, so `open` is false.
- A helper whose file has not been written for more than 30 minutes is hidden, even if `open` is still true (a crashed or killed session).
- The chief and project manager rows keep `isRunning` and `RUNNING_MS` unchanged.
- A helper that filed a ticket keeps joining that ticket's row as today; that path does not use `isRunning`.

### 2. No mod change

The mod keeps writing on events only. No plugin version bump.

### 3. Tests

In the `where a root checkout TICKET HELPER snapshot lands` table in `agent-team/scripts/dashboard/api.test.ts`:

- New case: an open helper with no ticket, last written 5 minutes ago, is a placeholder in Writing tickets.
- Change the `finished, no ticket: nowhere` case: its quiet helper is past the 30 minute bound (`NOW - 31 * 60_000`) instead of `NOW - 61_000`, and still shows nowhere. The closed-`main` helper in the same case stays.

## Leaves out

- Making the mod rewrite the snapshot on a tick while the main turn is open (the ticket's second option).
- The look and order of the Writing tickets group (WISE-430).
- The chief and project manager running rules.
- The Gantt bars of a quiet placeholder row: `cleanWith` still closes a quiet session's `main` and task bars at its last write, so the bar stops there until the next event. The row itself stays.

## Calls I made

- Fixed it in the dashboard, not the mod. A dashboard-only change needs no plugin bump or `claude plugin update`, and does not make every open session rewrite its file every 5 seconds. The cost: a helper that crashed mid-turn without closing `main` shows for up to 30 minutes instead of about a minute.
- The upper bound is 30 minutes, the ticket's example. A helper that waits on a tool, a permission ask or a subagent rewrites its file then, so only stretches of pure model work with no tool call count against it.
- A separate constant for helpers, so the chief and project manager rows keep their 60 second rule (out of scope per the ticket).
- Left the quiet row's Gantt bars ending at the last write rather than drawing them to now; changing `cleanWith` would also change worktree sessions.

## Acceptance

- An open helper with no filed ticket, last written more than 60 seconds ago and less than 30 minutes ago, is in Writing tickets.
- A helper that finished, or whose file is more than 30 minutes old, is hidden.
- A helper that filed a ticket still joins that ticket's row and is not a placeholder.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the repo Test command pass.
