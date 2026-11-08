# As-built: Restart the dashboard server itself when its code changes

**Shipped:** in PR #241
**Ticket:** CW-239
**Spec:** [2026-11-08-cw-239-dashboard-server-restart-design.md](../specs/2026-11-08-cw-239-dashboard-server-restart-design.md)

## Differs from the spec

- The spec has `start.ts` stop the pid that `/health` reports. A server from before this change reports no pid, so for that case `start.ts` falls back to the pid in `dashboard.json`, and only when `ps` shows that process is `server.ts --port <port>`.
- The spec says `restartError` clears when a later version restarts cleanly. It also clears when the code returns to the version that is running (for example after reverting the broken edit), and the failed mark clears with it.
- After `start.ts` replaces a server, it writes `environmentId` from its own option, else from the old `dashboard.json`, so the thread-link id is kept.
