# As-built: Restart the dashboard server itself when its code changes

**Shipped:** in PR #241
**Ticket:** CW-239
**Spec:** [2026-11-08-cw-239-dashboard-server-restart-design.md](../specs/2026-11-08-cw-239-dashboard-server-restart-design.md)

## Differs from the spec

- The spec has `start.ts` stop the pid that `/health` reports. At the head, `start.ts` signals a pid (from `/health`, or the one in `dashboard.json` for a server from before this change, which reports none) only when it is above 1 and `ps` shows the process is `server.ts --port <port>`. Anything else is left running.
- The spec says `restartError` clears when a later version restarts cleanly. It also clears when the code returns to the version that is running (for example after reverting the broken edit), and the failed mark clears with it.
- After `start.ts` replaces a server, it writes `environmentId` from its own option, else from the old `dashboard.json`, so the thread-link id is kept.
- The spec has the old server wait for `/health` to answer with `code` equal to the new version. The swap accepts the child it just spawned, matched by pid, when its `code` is any string other than the old one, so a second edit during the wait does not roll back a good server.
