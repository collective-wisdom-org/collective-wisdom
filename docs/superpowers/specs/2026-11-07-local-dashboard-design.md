# Local dashboard: status pane and agent gantt in the browser

**Status:** Shipped
**Shipped:** in PR #174, with differences: [as-built](../as-built/2026-11-07-local-dashboard.md)
**Ticket:** [#173](https://github.com/collective-wisdom-org/collective-wisdom/issues/173)
**Follows:** CW-171 (#172), which gave the gantt cost column its price table.

## Intent

Today the Chief of Staff status (`status-pane`) and the agent Gantt (`agent-gantt`) live in terminal panes beside one Claude Code chat. They are only visible inside that terminal. The user runs the team from T3 Code threads and wants the same two views in a page they can open in T3's browser pane, started for them when they say `start the team`.

## Goals

- One local page for the repo the user is working in, showing:
  - the status view: the same groups, rows, risk and next step as `status-pane`;
  - the Gantt view: the same rows, tokens and cost as `agent-gantt`, one block per session working in this repo.
- Every ticket row links to its **issue** and its **PR** (when it has one), and has a **copy thread link** button.
- `start the team` starts the page's server if it is not running and opens it in T3's browser pane. It never blocks the start if that fails.
- The page does not depend on which T3 thread is focused: status comes from the repo's state file, so switching threads changes nothing.

## Non-goals

- Several repos on one page.
- Clickable thread links. T3 asks "open this link?" for `t3-thread://` links, and then lands on the current thread whatever ID the link holds (tried with a plain UUID, an `mcp:` ID and an escaped ID, 2026-11-07). That is T3's handler, not ours. The copy button is the stand-in.
- Acting from the page (approve, merge, change anything). It is read-only.
- Removing the terminal panes. They keep working as they do.
- Remote access or login. The server answers only on this machine.

## Anti-goals

- A page that shows state the user must not see in a screenshot: `pendingRelay` holds the user's own words and `note` is free text. The server sends a fixed list of fields, never the raw state.
- A second copy of the grouping or row logic that can drift from the panes.
- A dashboard that makes `start the team` fail or slow.

## Constraints

- Mods can write files: `$.fs.write(path, text)` replaces a whole file and creates its folders. There is no append. `$.session.id()` and `$.agent.list()` exist. `$.fs.read` takes an absolute path; `~` is not expanded (CW-171 design). Mod API types: the bundled `plugin-authoring` skill, `claude-code.d.ts`.
- `.agent-team/` is gitignored at the root checkout, and `status-pane` already finds the root checkout's state file from a worktree (`register.tsx`, `open`). The Gantt feed uses the same lookup.
- Tickets in this repo are GitHub issues; the repo URL is the `Repo` row of `docs/agents/project.md`. The tracker may differ in an app.
- Thread links need the T3 environment id. A script cannot call T3 tools; the Chief of Staff can (`t3_environment_read`).
- Scripts live in `agent-team/scripts/` and reach an app through the machine install at `~/.collective-wisdom/scripts/`. `AGENTS.md` sets the test rules: test the behavior the team relies on, one table-driven test per rule, tests not longer than the feature code.

## Approaches

1. **Local server reading files (chosen).** A small server on `127.0.0.1` serves a static page and one JSON endpoint built from `.agent-team/state.json` and per-session Gantt snapshot files the mod writes. The page polls every 5 seconds. Data survives a server restart because the files hold it.
2. Mods push events to the server over HTTP. Rejected: a server restart loses the Gantt, and the mods fail when the server is down.
3. A generated static HTML file, no server. Rejected: T3's browser pane wants an `http://` address, the page goes stale until something rewrites it, and the Gantt still needs the feed from option 1.

The user picked option 1 on 2026-11-07, and one repo as the scope.

## Design

### Calls the user made

- One repo, the one the Chief of Staff runs in.
- Option 1 above.
- Issue and PR links on rows. Thread links are a copy button, since the real ones do not work.

### How it fits together

```
mod (each session)  --writes-->  <root>/.agent-team/gantt/<sessionId>.json
Chief of Staff      --writes-->  <root>/.agent-team/state.json   (exists)
start script        --writes-->  <root>/.agent-team/dashboard.json  {pid, port, environmentId}
server  --reads all three + prices.json-->  GET /api  -->  page (polls every 5 s)
```

### The Gantt feed (calls I made)

- **Snapshot per session, not a log.** `$.fs.write` cannot append, so each session rewrites its own file, `.agent-team/gantt/<sessionId>.json`: `{ sessionId, cwd, updatedAt, total, rows }`. `rows` is what the mod's own `buildRows` returns (names, repo, start, end, tokens, cost, child count, with the price table applied), so the server needs no Gantt logic and no raw agent records. It is written after each change to `records`, and every 5 s tick while any agent is running. A failed write never throws into the session.
- **Dead sessions.** A closed or crashed session stops writing. The server marks a session `stale` when its `updatedAt` is over 30 s old while a row still has `end: null`, and sends bar ends capped at `updatedAt`. The page dims a stale session and stops its bars moving.
- The mod finds the root checkout the way `status-pane` does and falls back to the session's relative path.
- The server shows a session's file while its `updatedAt` is within 24 hours. Older files are ignored, and the start script deletes files older than 24 hours.

### The server

- **Node, run as TypeScript** (Node 24, which the repo already needs for `rows.test.ts`). It imports `groupTickets` from `status-pane/hooks/groups.ts`, by a path relative to the script (`../../.claude/mods/status-pane/hooks/groups.ts`, which holds in `agent-team/` and through `~/.collective-wisdom`). That file imports only types, so plain Node runs it (checked with Node 26 on 2026-11-07). The Gantt rows come ready-made from the snapshot files. `mods/agent-gantt/` is outside the machine install, so the server never imports from it. If `node` is missing or older than 24, the start script prints one line saying so and the Chief of Staff reports it once.
- Lives in `agent-team/scripts/dashboard/` (server, start script, static page). Reached at `~/.collective-wisdom/scripts/dashboard/`.
- Binds `127.0.0.1` only, answers `GET` only, and rejects a request whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>` (DNS rebinding).
- `/api` returns a fixed shape:
  - `status`: groups from `groupTickets`, each row `{ id, title, risk, next, stage, issueUrl, prUrl, threadLink }`. Nothing else from state.
  - `gantt`: per session, `{ sessionId, cwd, updatedAt, stale, total, rows }`, each row only `{ id, depth, name, repo, start, end, tokens, cost, childCount }`, `name` cut to 60 characters. A null cost means no price table, as in the pane. Prices are the mod's job now, so the server does not read `prices.json`.
  - `generatedAt`.
- Links:
  - `issueUrl`: `<Repo URL>/issues/<N>` when the tracker is GitHub (read from `docs/agents/project.md`). Any other tracker: no link in this version, plain ID.
  - `prUrl`: `<Repo URL>/pull/<pr>` when the ticket's `pr` is a whole number (`cos_state.py` stores a number). Any other value: no link.
  - `threadLink`: `<t3-thread://v2/<environmentId>/<childThreadId>>` when both exist.
- Never throws on a bad or half-written file: it keeps the last good value, as `status-pane` does.

### The start script and the Chief of Staff

- `dashboard/start.ts` (run by the Chief of Staff): reads `.agent-team/dashboard.json`; if its pid is alive and answers on its port, prints the URL and exits; otherwise starts the server detached on the repo's port and writes `dashboard.json`. The port is the same every time for a repo: 47000 plus a hash of the root checkout's path (mod 1000), probing upward only if that one is taken by something else. So a restart does not break an open T3 tab, and two repos each get a page.
- `startup.md` § Setup gets one step after the state exists: write the T3 environment id into `dashboard.json` (the Chief of Staff reads it with `t3_environment_read`), run the start script, and open the URL in T3's browser pane if `preview_status` lists no tab at that URL. A failure is one line in the start report and does not stop the start.
- `resume` and take-over run the same step.

### The page

- Plain HTML, CSS and JavaScript, no build step and no framework. Two sections: Status (groups as in the pane) and Agents (one Gantt block per session).
- The "now" end of a running bar moves on the page's own clock between polls.
- Row cells: ticket ID linking to the issue, title, risk, next step, a PR link, and a copy button for the thread link. `http://127.0.0.1` counts as a secure context, so the clipboard works.
- Dark and light follow the browser.

### What is left to the builder

- Layout, colors, bar rendering and column widths on the page.
- Whether the mod needs a file-write permission declared in its manifest, and `claude plugin validate` for the `HOME` and file reads it makes.
- Bumping the two mod versions (`plugin.json`), as the README requires.
- The folder layout inside `agent-team/scripts/dashboard/` and the file names there.

### Tests

Per `AGENTS.md`: one table-driven test for the `/api` field whitelist (a state with `pendingRelay` and `note` set must not leak them), one for the snapshot rules (23 h kept, 25 h dropped; a snapshot 31 s old with a running row is `stale` and its bar ends are capped; the `gantt` row whitelist), one for the start script's idempotence and dead-pid recovery, one for the `Host` check. The existing `rows.test.ts` and `groups.test.ts` keep covering the shared logic.

## Sequence

CW-171 is merged (#172, `00b9a63`), so this builds on main. The Gantt snapshot write and the server can be one ticket; the `startup.md` step can ship in the same PR or a second one, the builder's call.
