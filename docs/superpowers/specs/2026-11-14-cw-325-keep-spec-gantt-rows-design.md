# CW-325: Keep the spec phase on a ticket gantt after the build session starts

**Status:** Draft
**Ticket:** [#325](https://github.com/collective-wisdom-org/collective-wisdom/issues/325)

## Goal

A ticket whose child switched model between spec and build shows its spec rows and its build rows on the gantt, live and in `.agent-team/gantt-history.json`.

## Cause, confirmed

Checked on CW-324 (worktree `t3-f7aaf98e-b4700a07ea9900c4`) from the Claude Code transcript and the live snapshot.

- The worktree has one transcript, `1054b40b-2b62-4207-b300-07fb3c26e6cd.jsonl`. The spec prompt (`TEAM MODE. Run /ship-loop for CW-324`, 22:54:14 UTC) and the build relay (`CHIEF OF STAFF: the user approved the spec`, 22:56:31 UTC) both carry that session id. Spec and build are one session.
- The model is `claude-opus-5-5` up to the relay and `claude-sonnet-5-5` from the first reply after it. That is the Chief of Staff's `t3_thread_configure` model switch.
- The snapshot `.agent-team/gantt/1054b40b-….json` has `heading: null` and two rows. The first, the `build` task, starts at 1794696991593 (22:56:31.593 UTC), the relay's time. The main record starts there too, and the `heading` atom, which the spec prompt would have set to `TEAM MODE`, is unset.
- So the switch restarts the provider on the same session id, the mod's atoms come back empty (`records`, `heading`, `ticket`, `request`), and the first `writeSnapshot` overwrites `<sessionId>.json` with the build rows only.
- `gantt-history.json` is keyed by session id and a newer snapshot replaces its own entry (`record` in `dashboard/history.ts`), so the history loses the spec rows too. Fixing the snapshot fixes the history.

CW-323 (`t3-23688694-09b9e71d49bee506`, session `de775c3f-…`) looks the same: one transcript, `heading: null`, first row `build`.

## Design

Keep the earlier rows when a restarted mod rewrites its session's snapshot.

1. **Read the old file once.** In `register.tsx`, the first `writeSnapshot` after the module loads reads the existing `<root>/.agent-team/gantt/<sessionId>.json` (after the same link and folder checks the write does). A missing, unreadable or bad file, or one whose `sessionId` is not this session's, gives nothing. What it read is kept in a module variable, like `root`, and not read again.
2. **Pick the earlier rows.** A new pure function in `snapshot.ts`, `earlierRows(old, mainStart)`, takes the parsed old snapshot and the current main record's `start`, and returns:
   - only the old rows that started before `mainStart`. If the atoms survived (no restart), `mainStart` is the session's real start and nothing qualifies, so no row is doubled.
   - each with its id prefixed `r<old updatedAt>:`, so `main:task:0` of the spec does not clash with `main:task:0` of the build. A row from a second restart keeps its prefix and gets another, so ids stay unique.
   - each closed at the old file's `updatedAt`: an `end: null` becomes that time and an open last segment ends there, since that process is gone.
3. **Write both.** Each `writeSnapshot` writes the earlier rows first, then the rows `buildRows` makes now. The rows keep their depth, so the dashboard draws the spec task with its subagents above the build task.
4. **Fill the unset fields.** When the current `heading`, `ticket` or `request` is null, the snapshot uses the old file's value, so a team session keeps its `TEAM MODE` or `TICKET HELPER` heading after a restart.
5. **Tests**, table-driven, in `snapshot.test.ts`: one table for `earlierRows` covering a restart (old rows before `mainStart` kept, prefixed and closed), no restart (all old rows at or after `mainStart`, nothing kept), a second restart (already prefixed rows kept with a new prefix), a bad old snapshot (no `rows` array, wrong `sessionId`), and a row still running in the old file. One case runs a full rewrite: old snapshot plus new `buildRows` output gives spec rows then build rows.

## Leaves out

- The session `total`. It comes from `$.session.usage()`; whether that keeps the spec's cost across a restart is not checked here. The CW-324 snapshot's total (about $1.54) suggests it does.
- The spend ledger (`spend.json`), which reads its own source.
- Stopping the provider restart on a model switch. That is Claude Code and T3 behavior.
- Past tickets: CW-323 and CW-324's spec rows are already gone and are not rebuilt.
- The Cursor hook (`cursor.ts`), which writes its own file per event.
- CI wait time on the gantt (CW-323).

## Calls I made

- The fix is in the mod (keep the rows on rewrite), not a second history file per session. The session id does not change, so there is no "spec session's own file" to keep.
- "Earlier" means started before the current main record. That is what tells a restart from a reload with the atoms intact, without a new stored marker.
- Earlier rows are drawn closed at the old file's last write, not at the restart time. Between the two the session did nothing the mod saw.
- Ids get an `r<updatedAt>:` prefix. The dashboard's live "turn in progress" check matches only `main` and `main:task:N`, so prefixed rows never count as running, which is right for rows of a finished process.
- The old file is read once per module load, not per write. Later writes in the same process reuse it.
- The cause is recorded on the ticket in a comment, as the ticket asks.

## Touches

None of: data, money, auth, user email, migrations. The mod reads one more file, inside the folder it already writes.
