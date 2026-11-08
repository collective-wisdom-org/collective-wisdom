# As-built: Back up the dashboard spend ledger and gantt history

**Shipped:** in PR #243
**Ticket:** CW-238
**Spec:** [2026-11-08-cw-238-dashboard-backup-design.md](../specs/2026-11-08-cw-238-dashboard-backup-design.md)

## Differs from the spec

- The spec does not say that `--force` takes its safety copy without pruning old sets. It does, so `--force` can never push out a good copy.
- A current file that is not valid JSON is not saved in the `--force` safety copy, because backup never saves invalid JSON.
- With `--force`, an existing file that no backup holds a copy of is kept, not removed.
- A file restore can't write is reported as `refused` and the command exits 1.
- `restore` is asynchronous (it checks for a running dashboard); `backup` is not. The `healthy` check moved from `start.ts` to `server.ts` and is exported there.
- A skipped file (missing, linked or invalid) keeps its newest valid copy: backup carries it into the new set, so pruning old sets never drops the last good copy.
- Backup does not refuse a missing `.agent-team`; it writes nothing and reports `unchanged`. Restore refuses a `--root` that is not a folder, and creates only `.agent-team`.
- The spec's one-line note in `chief-of-staff.md` was dropped in the compaction pass; the README holds the backup text.
