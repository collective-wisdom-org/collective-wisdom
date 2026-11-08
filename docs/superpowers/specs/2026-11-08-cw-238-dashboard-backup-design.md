# CW-238: Back up the dashboard spend ledger and gantt history

**Status:** Shipped
**Shipped:** in PR #243, with differences: [as-built](../as-built/2026-11-08-cw-238-dashboard-backup-as-built.md)
**Ticket:** [#238](https://github.com/collective-wisdom-org/collective-wisdom/issues/238)

## Goal

Losing a disk or getting one bad write no longer wipes out the spend ledger and the gantt history. A backup keeps several dated copies of them outside the root checkout, and a restore puts the latest good copy back.

## Today

Facts from `main` at `bd5602a`.

- `.agent-team/` is gitignored and exists only in the root checkout. It holds `state.json`, `spend.json`, `gantt-history.json`, `gantt/` (session snapshots), `dashboard.json` and `state.lock`.
- `agent-team/scripts/dashboard/server.ts` loads `spend.json` and `gantt-history.json` at start, keeps them in memory, and rewrites each one every 30 seconds when it changed (`recordRound`, `save`, `writeJson`). If the server starts while a file is missing or unreadable, it starts from an empty ledger and its first save overwrites the old file.
- `start.ts` refuses a `.agent-team` that is not a real folder, prunes `gantt/*.json` older than a day, and writes `dashboard.json` through a temp file and a rename. `readRegular` in `server.ts` reads a file only when it and its folders are not links.
- The Chief of Staff runs `node ~/.collective-wisdom/scripts/dashboard/start.ts --root <root checkout>` at `start the team`, `resume` and `take over` (`chief-of-staff/startup.md` step 4).
- Nothing copies these files anywhere.

## Design

### 1. `agent-team/scripts/dashboard/backup.ts`

A new module with two exported functions and a command line. It reuses `readRegular` from `server.ts`.

- **Files.** `spend.json`, `gantt-history.json`, `state.json`. Nothing else in `.agent-team/` is ever read or written by it (`dashboard.json`, `state.lock`, `gantt/` and temp files are left alone).
- **Location.** `backupDir(root)` returns `~/.agent-team-backups/<name>-<hash>/`, where `<name>` is the root checkout's folder name with anything outside `[A-Za-z0-9._-]` replaced by `-`, and `<hash>` is the first 8 hex characters of the SHA-1 of the root path (the same input `portFor` uses). Two checkouts with the same folder name get different folders. `--dest <dir>` on the command line overrides the location, for tests and for anyone who wants it elsewhere.
- **`backup({ root, dest?, keep = 14, now })`.**
  1. Refuses (returns an error, writes nothing) when `<root>/.agent-team` is missing or not a real folder, or when `~/.agent-team-backups`, the repo folder or `--dest` exists and is not a real folder.
  2. Reads each file with `readRegular`. A file that is missing, a link, or not valid JSON is skipped and named in the result, so a broken file never pushes a good copy out.
  3. If no file is left, or each file left is byte-equal to the copy in the newest set, it writes nothing and reports `unchanged`.
  4. Otherwise it creates the folders it needs (mode `0700`) and a new set folder named by the UTC time, `YYYYMMDDTHHMMSSZ` (with `-2`, `-3` if that name is taken), writes each file there with mode `0600` (`wx` flag, so nothing is overwritten and no link is followed), and only then deletes the oldest sets beyond `keep`. Only folders whose name matches the set pattern are counted or deleted, and a link among them is never followed or removed.
- **`restore({ root, dest?, force = false })`.**
  1. Same refusals as backup for `.agent-team` and the backup folders. A missing `.agent-team` is created (as `start.ts` does); an existing one must be a real folder.
  2. Refuses while a dashboard for this root is answering on the port in `dashboard.json` (the `healthy` check in `start.ts`, moved to an export), because the running server would overwrite the restored files from memory within 30 seconds. The message says to stop it first.
  3. For each of the three files, takes the newest set that holds a valid JSON copy of it.
  4. A file that is missing in `.agent-team` is written back. A file that exists is left alone unless `--force` is given; then the current file is first copied into a new set (so `--force` can be undone) and replaced. Writes go through a temp file and a rename, so a link at the target is replaced, not followed. A target that exists and is not a regular file is refused.
  5. Reports each file as restored (with the set it came from), kept, or not in any backup.
- **Command line.** `node backup.ts --root <dir> [--dest <dir>] [--keep <n>]` and `node backup.ts restore --root <dir> [--dest <dir>] [--force]`. One line per file on stdout, exit 0 on success, 1 on a refusal, 2 on bad arguments. Needs Node 24, like `start.ts`.

### 2. Trigger: the dashboard takes the backups

- **`start.ts`** calls `backup` on every run, after the `.agent-team` folder check and before it reuses or starts a server, so each `start the team`, `resume` and `take over` keeps a copy of what the last run left. A failed backup prints one line to stderr and the start carries on; it never stops the dashboard.
- **`server.ts`** calls `backup` once every 24 hours from its own timer, for a Chief of Staff that runs for days without a restart. Same rule: a failure is ignored.
- `unchanged` sets are not written, so a quiet repo does not cycle its good copies out. 14 sets at about 120 KB is under 2 MB per repo.

### 3. Docs

- `README.md` § Local dashboard: one short paragraph on where the backups go, when they are taken, how many are kept, and the two commands (`node ~/.collective-wisdom/scripts/dashboard/backup.ts restore --root <root checkout>`, stop the dashboard first).
- `agent-team/docs/agents/chief-of-staff.md`: half a line next to the dashboard start that it also takes a backup.

## Tests

In `agent-team/scripts/dashboard/backup.test.ts`, run by the existing `node --test` command, on temp folders with `--dest`:

- **Backup rule, table-driven:** files present, one missing, one invalid JSON, one a link, nothing changed since the last set, and `keep` exceeded. Each row checks which files land in the new set (or that no set is made) and which sets remain. The runtime files placed in `.agent-team` never appear in a set.
- **Refusals, table-driven:** `.agent-team` a link, backup folder a link, repo folder a link, a file in a set that is a link (not followed on restore). Each refuses and writes nothing outside the expected place.
- **Restore rule, table-driven:** all files missing brings back the newest valid copies; an existing file is kept without `--force` and replaced with `--force` after a new set holds the old one; a newest set with a broken copy falls back to the older set.
- **Start hook:** one check that `startDashboard` with a temp root makes a set, and still starts when the backup folder is refused.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.

## Non-goals

- Sharing state between machines or users, or any off-machine copy.
- Backing up the tracker, threads, git history, `dashboard.json`, `state.lock` or `gantt/` snapshots.
- Fixing the server's habit of starting from an empty ledger when `spend.json` is unreadable. The backup taken by `start.ts` before the server starts covers it; a guard in `server.ts` is its own ticket if wanted.
- A restore that runs by itself. Restore is always a command someone runs.

## Calls I made (surprising first)

- **Backups go to `~/.agent-team-backups/<folder name>-<hash>/` in the home folder.** It is outside the root checkout, survives deleting or re-cloning the repo, and needs no setup. It does not survive a lost disk. Alternatives: a folder next to the root checkout (`<parent>/.agent-team-backups/`, same disk, lost with a re-clone of the parent); a cloud-synced folder such as iCloud Drive (survives the disk, but only on machines that have it, and spend data leaves the machine); a `Backup location` row in `project.md` that defaults to the home folder (adds a key every app has to carry). `--dest` stays either way.
- **The dashboard takes the backups, not the Chief of Staff.** `start.ts` backs up on every run and the server once a day. This keeps the Chief of Staff skill unchanged and puts the backup next to the only writer of the two files, and the start-time copy is taken before a new server can overwrite anything. Alternatives: a Chief of Staff step in `startup.md` that runs `backup.ts` (one more line in a long start-up, and missed when the dashboard is started by hand); a backup inside every `save` that changes a file (most current, but a set every 30 seconds while agents run); manual only (simple, and easy to forget).
- **Keep 14 sets, skip a set when nothing changed.** About two weeks of start-ups; a quiet repo keeps old copies instead of 14 identical ones.
- **`state.json` is backed up too**, as the ticket allows. It is small and saves rebuilding from the tracker.
- **A file that is not valid JSON is never backed up**, so a bad write can't push out the good copies. Restore likewise skips a broken copy and falls back to an older set.
- **Restore fills only missing files unless `--force`,** and `--force` first saves the current files as a new set.
- **Restore refuses while the dashboard is running,** since the server would overwrite the restored files from memory. Stopping it is left to the user (kill the pid in `dashboard.json`); the next `start.ts` brings it back.
- **The backup code is TypeScript next to `start.ts`,** not Python next to `cos_state.py`, so it shares `readRegular` and the link rules and runs from the same `start.ts` call.
- **Folders `0700`, files `0600`,** because the ledger is spend data.

Touches: data (writes a new folder under the home folder, and restore can replace `.agent-team` files with `--force`). No money, auth, user email or migrations.
