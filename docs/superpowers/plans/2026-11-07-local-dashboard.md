# Local Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only local page, opened in T3's browser pane by `start the team`, that shows this repo's Chief of Staff status and its sessions' agent Gantt.

**Architecture:** A Node server in `agent-team/scripts/dashboard/` serves a static page and `/api`, built from `.agent-team/state.json` and per-session snapshot files that the `agent-gantt` mod rewrites. A start script makes it idempotent; one new step in `startup.md` runs it.

**Tech Stack:** Node 24 (runs `.ts` by type stripping, `node:test`, `node:http`), plain HTML and JavaScript for the page, the existing mod API.

**Spec:** `docs/superpowers/specs/2026-11-07-local-dashboard-design.md`

**Before Task 1:** file the ticket with `write-ticket` and branch as `docs/agents/project.md` says (`feat/cw-<N>-local-dashboard`). The spec and this plan are still uncommitted; Task 1's commit includes both. The spec says "bump the two mod versions"; only `agent-gantt` changes, so bump that one (`plugin.json`, and the marketplace entry if it carries a version).

## Global Constraints

- Server binds `127.0.0.1` only, answers `GET` only, and rejects a `Host` header that is not `127.0.0.1:<port>` or `localhost:<port>` with 403.
- `/api` sends a fixed list of fields. Status rows: `{ id, title, risk, next, stage, issueUrl, prUrl, threadLink }`. Gantt rows: `{ id, depth, name, repo, start, end, tokens, cost, childCount }`, `name` cut to 60 characters. Never `pendingRelay`, `note`, or any other state key.
- A snapshot is shown while its `updatedAt` is within 24 hours. It is `stale` when `updatedAt` is over 30 s old and a row has `end: null`; a stale session's running rows are sent with `end = updatedAt`.
- Port: `47000 + (hash of the root checkout path) mod 1000`, probing upward only if another process holds it.
- Links: `issueUrl` = `<Repo URL>/issues/<digits after the last "-" in the ticket id>`, only when `project.md` says tickets are GitHub issues; `prUrl` = `<Repo URL>/pull/<pr>` only when `pr` is a whole number; `threadLink` = `<t3-thread://v2/<environmentId>/<childThreadId>>`, only when both exist.
- The status grouping is `groupTickets` from `agent-team/.claude/mods/status-pane/hooks/groups.ts`, imported by relative path (`../../.claude/mods/status-pane/hooks/groups.ts`). The server never imports from `mods/agent-gantt/`.
- Snapshot files live at `<root>/.agent-team/gantt/<sessionId>.json`; the root is found the way `status-pane/hooks/register.tsx` `open` finds it. A failed write never throws into the session. A failure to start the dashboard never blocks `start the team`.
- Tests follow `AGENTS.md`: table-driven, one per rule, and test lines not above feature code lines. Node tests run with `node --test`.

## Review Focus

Each line has its test in the task named.

1. No `.agent-team/state.json`, or an empty or half-written one: the page shows an empty status, not an error (Task 1, Task 2).
2. A snapshot file with bad JSON or the wrong shape sits in the `gantt` folder: it is skipped and the others still show (Task 1).
3. A ticket id that is not `PREFIX-number`, or a `pr` that is not a whole number: no link, no crash (Task 1).
4. A session id with `/` or `..` in it: the mod writes nothing outside `.agent-team/gantt/` (Task 5).
5. A ticket title or next step containing `<script>`: the page shows it as text (Task 4).

---

### Task 1: The `/api` builder

**Files:**
- Create: `agent-team/scripts/dashboard/api.ts`
- Test: `agent-team/scripts/dashboard/api.test.ts`

**Interfaces:**
- Consumes: `groupTickets(state: unknown): Group[]` from the status-pane `groups.ts`.
- Produces, in `api.ts`:
  - `type SnapshotRow = { id: string; depth: number; name: string; repo: string; start: number; end: number | null; tokens: number; cost: number | null; childCount: number }`
  - `type Snapshot = { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: SnapshotRow[] }`
  - `type Api = { generatedAt: number; status: { name: string; count: number; rows: StatusRow[] }[]; gantt: { sessionId: string; cwd: string; updatedAt: number; stale: boolean; total: number | null; rows: SnapshotRow[] }[] }`
  - `repoUrlFromProject(markdown: string): { url: string; isGithubIssues: boolean } | null`
  - `buildApi(input: { state: unknown; snapshots: unknown[]; repo: { url: string; isGithubIssues: boolean } | null; environmentId: string | null; now: number }): Api`

- [ ] **Step 1: Write the failing tests** in `api.test.ts`
  - `whitelist`: a state whose ticket has `pendingRelay: "my words"` and `note: "free text"` gives `JSON.stringify(buildApi(...))` containing neither string.
  - `links` (table): `CW-171` + `pr: 172` + `childThreadId: "t1"` + environment `"env"` gives `issueUrl` `https://github.com/o/r/issues/171`, `prUrl` `.../pull/172`, `threadLink` `<t3-thread://v2/env/t1>`. Rows for `ABC` (no number), `pr: "172"`, `pr: null`, no environment id, and `isGithubIssues: false` each drop exactly the link they cannot build.
  - `snapshots` (table, `now` fixed): 23 h old kept; 25 h old dropped; 31 s old with a row `end: null` gives `stale: true` and that row's `end === updatedAt`; 31 s old with all rows ended is not stale; a snapshot that is a string, lacks `rows`, or has `rows` not an array is skipped; a row `name` of 80 characters comes back 60.
  - `empty`: `state` of `null`, `{}`, `"x"` gives `status: []` and no throw.
  - `repoUrlFromProject`: the real `docs/agents/project.md` text gives `{ url: "https://github.com/collective-wisdom-org/collective-wisdom", isGithubIssues: true }`; text with no `Repo` row gives `null`.
- [ ] **Step 2: Run** `node --test agent-team/scripts/dashboard/api.test.ts`. Expected: FAIL, module not found.
- [ ] **Step 3: Implement** the four exports in `api.ts`. `buildApi` takes the groups from `groupTickets`, then adds `stage`, `issueUrl`, `prUrl`, `threadLink` to each row by looking the id up in `state.tickets`. Validate snapshots by shape and copy only the whitelisted fields; never spread an input object. `repoUrlFromProject` reads the `Repo` table row's `<https://...>` URL, and `isGithubIssues` is true when the text contains `Tickets are GitHub issues`.
- [ ] **Step 4: Run** the same command. Expected: all PASS.
- [ ] **Step 5: Commit**
```bash
git add docs/superpowers/specs/2026-11-07-local-dashboard-design.md docs/superpowers/plans/2026-11-07-local-dashboard.md agent-team/scripts/dashboard/api.ts agent-team/scripts/dashboard/api.test.ts
git commit -m "feat: build the local dashboard API from state and snapshots"
```

### Task 2: The server

**Files:**
- Create: `agent-team/scripts/dashboard/server.ts`
- Test: `agent-team/scripts/dashboard/server.test.ts`

**Interfaces:**
- Consumes: `buildApi`, `repoUrlFromProject` from Task 1.
- Produces: `startServer(opts: { root: string; port: number }): Promise<{ port: number; close(): Promise<void> }>`. CLI: `node server.ts --root <dir> --port <n>`. Routes: `GET /` and `GET /app.js` (files from `./page/`), `GET /api` (JSON), `GET /health` (`{ ok: true, root }`). Anything else: 404; non-`GET`: 405.

- [ ] **Step 1: Write the failing tests** in `server.test.ts`, each starting `startServer` on port 0 against a temp root and calling it with `fetch`, closing it afterwards:
  - `host` (table): `Host: 127.0.0.1:<port>` and `localhost:<port>` get 200 on `/api`; `evil.example`, `127.0.0.1:1` and a missing Host get 403.
  - `method`: `POST /api` gets 405.
  - `degraded` (table): no `.agent-team/`, a half-written `state.json` (`{"tickets":`) and a `gantt/` holding one bad-JSON file and one good snapshot each give 200 and valid JSON; the last case still lists the good session; after a good read, writing a half-written `state.json` keeps the previous `status`.
- [ ] **Step 2: Run** `node --test agent-team/scripts/dashboard/server.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `startServer` with `node:http`, listening on `127.0.0.1`. On each `/api` call read `state.json`, every `gantt/*.json`, `dashboard.json` (`environmentId`) and `docs/agents/project.md` under `root`, parse each in its own `try`, and keep a module-level last good value for `state` so a half-written file does not blank the page. Compare `Host` exactly against `127.0.0.1:<port>` and `localhost:<port>` using the port actually bound.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: serve the local dashboard API on localhost only` (add both files).

### Task 3: The start script

**Files:**
- Create: `agent-team/scripts/dashboard/start.ts`
- Test: `agent-team/scripts/dashboard/start.test.ts`

**Interfaces:**
- Consumes: the CLI of Task 2.
- Produces: `portFor(root: string): number`; `startDashboard(opts: { root: string; environmentId?: string; basePort?: number }): Promise<{ url: string; started: boolean }>`; CLI `node start.ts --root <dir> [--environment-id <id>]`, printing the URL. Writes `<root>/.agent-team/dashboard.json` as `{ pid, port, environmentId }`.

- [ ] **Step 1: Write the failing tests** in `start.test.ts`:
  - `portFor`: same root twice gives the same port; ten different roots all fall in 47000-47999.
  - `idempotent`: with a temp root and `basePort` set to a free high port, `startDashboard` returns `started: true`, a second call returns `started: false` and the same `url`, and `fetch(url + "health")` answers; the test kills the pid afterwards.
  - `dead pid`: a `dashboard.json` naming a pid that is gone and a port nothing answers on is replaced, giving `started: true`.
  - `port taken`: another listener already holds the base port without answering `/health` as ours; the result uses a port above it.
  - `environment id`: calling again with a new `environmentId` while running rewrites it in `dashboard.json` and keeps `started: false`.
  - `prune`: files in `.agent-team/gantt/` older than 24 h are deleted on start; newer ones stay.
- [ ] **Step 2: Run** `node --test agent-team/scripts/dashboard/start.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `portFor` from the first four bytes of a `node:crypto` sha1 of `root`. "Running" means `dashboard.json` exists, `/health` on its port answers with this `root`. Start the server with `spawn(process.execPath, [serverPath, ...], { detached: true, stdio: "ignore" }).unref()`, wait up to 3 s for `/health`, then write `dashboard.json`. `server.ts` is found next to `start.ts` by `import.meta.dirname`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: start the local dashboard once per repo` (add both files).

### Task 4: The page

**Files:**
- Create: `agent-team/scripts/dashboard/page/index.html`, `agent-team/scripts/dashboard/page/app.js`
- Test: `agent-team/scripts/dashboard/page/app.test.js` (only `esc`-style rendering, see Step 1)

**Interfaces:**
- Consumes: the `/api` shape of Task 1.
- Produces: `app.js` exports (when loaded by Node) `renderStatus(groups): string` and `renderGantt(sessions, now): string`; in the browser it polls `/api` every 5000 ms and sets `innerHTML` from those. A running bar's right end uses `Date.now()` between polls.

- [ ] **Step 1: Write the failing test** `app.test.js`: a status row with `title: "<script>alert(1)</script>"` and `next: "a & b"` renders with `&lt;script&gt;` and `a &amp; b` and without a literal `<script>`; a row with no `prUrl` has no PR anchor; a row with `threadLink` has a `button` whose `data-copy` equals the link.
- [ ] **Step 2: Run** `node --test agent-team/scripts/dashboard/page/app.test.js`. Expected: FAIL.
- [ ] **Step 3: Implement** the two render functions with every dynamic string passed through one `esc()`. Page layout, colors, bar drawing and column widths are yours; follow the spec's "The page" section (ticket id links to the issue, title, risk, next, PR link, copy button; one Gantt block per session; stale sessions dimmed with bars frozen). The copy button calls `navigator.clipboard.writeText` from a delegated click handler. Clock and token formats: `HH:MM`, `950` / `12.3k` / `1.2M`, `$0.42` or `–`, as in `mods/agent-gantt/hooks/format.ts`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Look at it.** Run `node agent-team/scripts/dashboard/start.ts --root "$PWD"`, open the printed URL in a browser, and confirm the status groups match what `status-pane` shows for `.agent-team/state.json`. Expected: same groups and counts.
- [ ] **Step 6: Commit** `feat: add the local dashboard page`.

### Task 5: The Gantt snapshot in the mod

**Files:**
- Create: `mods/agent-gantt/hooks/snapshot.ts`, `mods/agent-gantt/hooks/snapshot.test.ts`
- Modify: `mods/agent-gantt/hooks/register.tsx` (the `refresh` function and imports), `mods/agent-gantt/.claude-plugin/plugin.json` (version `0.1.1` to `0.1.2`), and the marketplace entry if it names a version

**Interfaces:**
- Consumes: `buildRows(records, agents, prices): Row[]` from `rows.ts`.
- Produces, in `snapshot.ts`: `snapshotName(sessionId: string): string | null` (the file name `<id>.json`, or `null` unless the id matches `^[A-Za-z0-9_-]{1,80}$`); `buildSnapshot(args: { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: Row[] }): string` (JSON text of `{ sessionId, cwd, updatedAt, total, rows }`).

- [ ] **Step 1: Write the failing test** in `snapshot.test.ts`: `snapshotName` table: `"abc-123_X"` gives `"abc-123_X.json"`; `""`, `"../x"`, `"a/b"`, `"a.b"`, 81 characters and `"x\u0000"` give `null`.
- [ ] **Step 2: Run** `node --test mods/agent-gantt/hooks/snapshot.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `snapshotName` and `buildSnapshot`.
- [ ] **Step 4: Run** the same command and `node --test mods/agent-gantt/hooks/rows.test.ts`. Expected: PASS both.
- [ ] **Step 5: Modify `register.tsx`.** Add `writeSnapshot($: EngineInterface): Promise<void>`: resolve the root checkout the way `status-pane/hooks/register.tsx` `open` does (cache it), build rows with `buildRows(records, await $.agent.list(), table)`, take `total` from `(await $.session.usage()).cost?.usd ?? null`, and `$.fs.write` `<root>/.agent-team/gantt/<name>` from `snapshotName(await $.session.id())`. Skip silently when the name is `null`. Wrap the whole body in `try/catch`. Call it as the last line of `refresh`, which already runs on every change and every 5 s tick while an agent runs.
- [ ] **Step 6: Check the mod** with `claude plugin validate mods/agent-gantt` (it lists the file and `HOME` reads and writes; add whatever the manifest needs for the write). Then start a session in this repo with the mod, spawn one subagent, and confirm `.agent-team/gantt/<sessionId>.json` appears and updates. Expected: the file holds that session's rows.
- [ ] **Step 7: Commit** `feat: write the agent-gantt rows for the local dashboard`.

### Task 6: Start it with the team, docs and CI

**Files:**
- Modify: `agent-team/.claude/skills/chief-of-staff/startup.md` (§ Setup, after step 4; and the resume-mode line in step 2), `agent-team/.claude/skills/chief-of-staff/rotation.md` (§ Thread rotation: Resume mode) and `agent-team/.claude/skills/chief-of-staff/SKILL.md` (the take-over command) where each lists what a resume or take-over runs, `README.md` (a short section next to the status-pane and gantt text), `AGENTS.md` (the `mods/` test line), `.github/workflows/ci.yml` (`mod-tests` job)
- Test: `agent-team/scripts/test_agent_files.py` and `test_call_sites.py` (run, not edited)

**Interfaces:**
- Consumes: the start script CLI of Task 3.
- Produces: the startup step text below.

- [ ] **Step 1: Add the startup step.** New step 5 in § Setup: read the T3 environment id with `t3_environment_read`; run `node ~/.collective-wisdom/scripts/dashboard/start.ts --root <root checkout> --environment-id <id>`; if the script prints a URL and `preview_status` lists no tab at it, `preview_open` it; on any failure (node missing or older than 24 behaves as a failure, with the script's one-line message) add one line to the start report and carry on. Say in resume mode (startup.md step 2, rotation.md § Resume mode) and in the take-over command that the same step runs there.
- [ ] **Step 2: CI and docs.** In `ci.yml` `mod-tests`, add `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/snapshot.test.ts`. In `AGENTS.md` extend the `mods/` test line to the same files. In `README.md`, one short section: what the page shows, that `start the team` opens it, the copy button for thread links and why (T3 does not open them from a browser).
- [ ] **Step 3: Run the whole checks.** `python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`. Expected: all pass.
- [ ] **Step 4: Try it end to end** from a T3 thread at the root checkout: say `start the team` (or run the startup step by hand), confirm the T3 browser pane opens the page, the status matches `status`, and a running subagent shows in the Agents section. Expected: both sections fill, and the page keeps updating.
- [ ] **Step 5: Commit** `feat: start the local dashboard with the team`.

---

## Self-review

- **Spec coverage:** goals (status, Gantt, links, start-up, thread independence) are Tasks 1-6; whitelist, stale, 24 h, Host check, port and prune are in Global Constraints with a test each; non-goals have no task by design; "left to the builder" items are named in Tasks 4 and 5.
- **Type consistency:** `Snapshot`/`SnapshotRow` in Task 1 match `buildSnapshot` output in Task 5 and the `Row` fields of `rows.ts`; `startServer`, `portFor` and `startDashboard` names are the same where they are used.
- **Proportion:** the plan is about twice the spec, mostly test lists and signatures.
