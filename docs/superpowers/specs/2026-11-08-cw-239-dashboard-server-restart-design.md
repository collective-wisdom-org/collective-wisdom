# CW-239: Restart the dashboard server itself when its code changes

**Status:** Draft
**Ticket:** [#239](https://github.com/collective-wisdom-org/collective-wisdom/issues/239)
**Related:** CW-230 (#230, page autoreload, shipped in PR #234).

## Goal

After a merge fast-forwards the root checkout, the running dashboard server swaps itself for one running the new code, on the same root and port, with no manual stop and rerun. The open tab keeps working through the swap and shows the new data on its own.

## Today

Facts from `main` at `bd5602a`.

- `~/.collective-wisdom` is a link to the root checkout's `agent-team/`, so a merge changes the files the server was loaded from. Node has already loaded them, so the process keeps serving the old code.
- `start.ts` spawns `server.ts` detached and returns early when `/health` answers `{ ok: true, root }` on the port in `.agent-team/dashboard.json`. Only `start.ts` writes that file (`{ pid, port, environmentId }`).
- The Chief of Staff runs `start.ts` at `start the team`, `resume` and `take over` only (`chief-of-staff/startup.md` Setup step 4).
- `server.ts` imports `api.ts`, `titles.ts`, `updated.ts`, `merged.ts`, `details.ts`, `spend.ts` and `history.ts`. `api.ts` imports `agent-team/.claude/mods/status-pane/hooks/groups.ts` and `mods/agent-gantt/hooks/rows.ts`.
- The page polls `/api` every 5 seconds. A failed poll shows `Could not refresh: ...` in `#error` and the next good poll clears it. A changed `version` (CW-230) reloads the tab.

## Design

The server watches its own code and replaces itself. Nothing else needs to be running, so the swap works between Chief of Staff sessions too.

1. **Which files.** `server.ts` exports `codeFiles(entry: string): string[]`. It reads `entry`, collects the relative import specifiers (`from './x.ts'`, `from '../y.ts'`, `import type` included) that end in `.ts` or `.js`, resolves them against the importing file's real folder, and follows them the same way. Bare specifiers (`node:fs`) and specifiers to files that don't exist are skipped. It returns the real paths, sorted, each once, `entry` included. Today that is `server.ts`, the seven modules it imports, `groups.ts` and `rows.ts`.
2. **Code version.** `codeVersion(files: string[]): string | null` is a 16-character SHA-256 prefix over each path and its contents, like `pageVersion`. Any unreadable file gives `null`. The server computes the file list and version once at start (`running`). `/health` adds `code: running` and `pid: process.pid`.
3. **Restart decision.** `server.ts` exports a pure factory `restartWatch(running)` returning `check(version) -> boolean` ("restart now?"):
   - `null` returns `false`.
   - A version equal to `running` returns `false` and clears any pending candidate.
   - A new version must be seen on two checks in a row before it returns `true`, so a checkout that is still writing files doesn't trigger a restart halfway.
   - A version marked failed (`failed(version)`) returns `false` until a different version shows up.
4. **Check loop.** Every 5 seconds the server recomputes `codeFiles` and `codeVersion` from its own `server.ts` (a new import shows up in the next check) and calls `check`. One restart runs at a time.
5. **Preflight.** On `true`, the server first runs `node --input-type=module -e "await import('<server.ts URL>')"` with a 15 second timeout. Importing `server.ts` loads every module and starts nothing (its `isMain` check is false). A non-zero exit (a syntax error, a missing export) marks the version failed, sets the restart error (step 8) and keeps the old server serving. The page never loses its server in this case.
6. **Swap.** On a clean preflight the server stops listening (`server.close()` and `closeAllConnections()`), spawns `server.ts --root <root> --port <port>` detached the way `start.ts` does, and waits up to 15 seconds for `/health` on that port to answer with this root and `code` equal to the new version.
   - **Up:** it rewrites `.agent-team/dashboard.json` as `{ pid: <new pid>, port, environmentId }` (keeping the file's `environmentId`) through the same temp-file-and-rename write `writeJson` already does, and exits.
   - **Not up:** it kills the child, listens on the port again with the old code, marks the version failed and sets the restart error. If the port can't be bound again, it exits, and the next `start.ts` starts a fresh server.
7. **The page.** The swap leaves the port closed for about as long as the new server takes to start (its first `git worktree list` runs before it listens). A poll in that gap shows `Could not refresh` once; the next poll reaches the new server and redraws. If the page files changed in the same merge, `version` differs and the tab reloads (CW-230). No other page change is needed for the swap.
8. **Reporting a failed restart.** `/api` adds `restartError: string | null`: `Server code changed but did not load: <first line of the error>` for the last failed version, `null` otherwise. `poll()` shows it in `#error` instead of clearing that line, so the tab says it is on old code. It clears once a later version restarts cleanly (the new server starts with `null`).
9. **`start.ts` catches up an older server.** When the server in `dashboard.json` is healthy for the root but its `/health` `code` differs from `codeVersion(codeFiles(server.ts))` computed by `start.ts` (a server from before this change has no `code`), `start.ts` sends `SIGTERM` to the pid `/health` reports, waits up to 3 seconds for the port to free, and starts a new server from that port as it does today. A server whose code matches is reused as today. This covers the one manual step this change would otherwise need: the server running when it merges has no watcher.

## Tests

- `server.test.ts`, one table-driven case for `codeFiles` on a temp folder: an entry importing `./a.ts` and `import type` from `../b/c.ts`, a bare `node:fs`, and a missing `./gone.ts` gives the entry, `a.ts` and `c.ts`; a cycle between two files lists each once. One assertion on the real `server.ts` that the list includes `api.ts`, `groups.ts` and `rows.ts`.
- `server.test.ts`, one table-driven case for `codeVersion`: same files give the same version, a changed file changes it, a missing file gives `null`.
- `server.test.ts`, one table-driven case for `restartWatch`: sequences of checks (with `failed` calls) and the expected answers, such as running `r` with `[r, x, x]` giving `[false, false, true]`, `[x, y, y]` giving `[false, false, true]`, `[x, r, x]` giving `[false, false, false]`, `null` never `true`, and a failed `x` giving `false` on every later `x` until `y` comes twice.
- `start.test.ts`, one case: a healthy server for the root whose `/health` reports a different `code` is stopped and replaced on the same port, and `dashboard.json` has the new pid.
- `app.test.js` is unchanged: the `#error` line is a one-line wiring change in `poll()`.

The swap itself (steps 5 and 6) is proved by hand in the PR: run the dashboard from the worktree, edit `api.ts`, see `/api` change and one server left with the right pid in `dashboard.json`; then add a syntax error and see the old server keep serving with `restartError` set.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes, and so does `python3 -I -m pytest -q agent-team/scripts`.

## Docs

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` says only the start script writes `.agent-team/dashboard.json`; it becomes "the dashboard scripts".
- `README.md` § Local dashboard gains one sentence: the server restarts itself on the new code after a merge, and the page says so if the new code fails to load.

## Non-goals

- Page autoreload for `index.html` and `app.js` (CW-230).
- Restarting the Chief of Staff or any other agent.
- A supervisor process, or a launchd or systemd unit.
- Zero-downtime handover on the port.
- Carrying page state across the swap.

## Calls I made

- **The server replaces itself; no supervisor.** A supervisor process would have to be restarted itself when its own code changes, and adds a second pid to track. The server already knows its root and port, so it can start its successor and step aside.
- **`start.ts` restarts a healthy server whose code differs** (step 9), using the pid `/health` reports. This goes past "detect and restart in the server" so the server running at merge time, which has no watcher, is caught up at the next Chief of Staff start-up without a manual stop. Killing the pid `/health` reports, not the one in `dashboard.json`, avoids killing an unrelated process that reused a stale pid.
- **No shutdown endpoint.** A GET `/shutdown` could be hit from any web page in the browser with a valid `Host` header, so the swap and `start.ts` use the process pid instead.
- **The file list is the import graph from `server.ts`, re-read on every check,** not a fixed list. A fixed list would go stale the next time a module is added. `import type` imports are followed too: a change there restarts the server for nothing, which is cheap.
- **Poll every 5 seconds, not `fs.watch`.** `fs.watch` misses changes made through the links and renames git uses on some systems; hashing ten small files every 5 seconds costs little. A new version must be seen twice in a row, so a restart lands 5 to 10 seconds after the files settle.
- **A preflight import before closing the port,** so a broken file never takes the page down; the swap's health wait covers what the preflight can't catch (a crash at start).
- **The old server rewrites `dashboard.json`** after the new one answers, because the new server can't know it replaced one. The ticket's "right pid and port" needs it.
- **A short gap, not zero downtime.** Node can't share a listening port between two unrelated processes on macOS without extra flags; one `Could not refresh` line during the swap is acceptable for a local page.
- **A failed version is not retried** until the code changes again, so a broken file doesn't trigger a preflight every 5 seconds.
- **The failure shows in the page's existing `#error` line,** the smallest change that keeps a stuck server from being silent.
- **Timeouts of 15 seconds** for the preflight and the health wait, since the new server runs `git worktree list` (up to 5 seconds) before it listens; `start.ts` keeps its 3 seconds.
