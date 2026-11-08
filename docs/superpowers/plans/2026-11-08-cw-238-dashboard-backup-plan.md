# CW-238 plan: back up the dashboard spend ledger and gantt history

**Spec:** `docs/superpowers/specs/2026-11-08-cw-238-dashboard-backup-design.md` (approved, backup folder `~/.agent-team-backups/`, dashboard takes the backups).

## Task 1: `backup.ts` and its tests
- `agent-team/scripts/dashboard/backup.ts`: `backupDir`, `backup`, `restore`, command line, per spec § Design 1. Reuse `readRegular` from `server.ts`.
- `agent-team/scripts/dashboard/backup.test.ts`: the table-driven tests in spec § Tests (backup rule, refusals, restore rule).
- Run: `node --test agent-team/scripts/dashboard/backup.test.ts`.

## Task 2: hook into `start.ts` and `server.ts`
- Export the `healthy` check from `start.ts` for restore's running-dashboard refusal (avoid an import cycle: put it where both can import it).
- `start.ts` calls `backup` after the `.agent-team` folder check; a failure prints one line to stderr and the start goes on.
- `server.ts` calls `backup` once every 24 hours from an unref'd timer; failures ignored.
- One test in `start.test.ts`: start makes a set, and still starts when the backup folder is refused.

## Task 3: docs
- `README.md` § Local dashboard paragraph and a half line in `agent-team/docs/agents/chief-of-staff.md` (spec § Docs). Plain sentences, no em dashes.

## Verify
`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`. Tests must use temp folders and `--dest`, never the real home folder.
