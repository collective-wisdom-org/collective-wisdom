# As-built: Local dashboard

**Shipped:** in PR #174
**Ticket:** CW-173
**Spec:** [2026-11-07-local-dashboard-design.md](../specs/2026-11-07-local-dashboard-design.md)

## Differs from the spec

- **Stale sessions.** The spec calls a session stale when its snapshot is over 30 s old and any row is still running. Every snapshot has a running `main` row, so live idle sessions showed as stale. Shipped: stale only when a non-main row is running and the snapshot is over 30 s old. When no subagent is running, the `main` row's end is `updatedAt`.
- **Where the mod writes.** The spec has the mod write a snapshot in every session. Shipped: only in a repo that has `docs/agents/project.md` or `.agent-team/state.json`, so installing the mod for the pane leaves no `.agent-team/` folder in unrelated repos.
- **Mod versions.** The spec says to bump two mod versions. Only `agent-gantt` changed, so only it moved (0.1.1 to 0.1.2).
- **Response headers.** The server also sends `X-Content-Type-Options: nosniff` on every response and a `Content-Security-Policy` on `/`. The spec does not mention them.
- **Status redraw.** The page redraws the Gantt every second but the status section only after a poll that changed it, so the "Copied" label and text selection survive.
- **Startup step.** The dashboard step sits in `startup.md` Setup step 4, before the full pass, and resume mode gets it through take-over step 4.1, not a separate run.
