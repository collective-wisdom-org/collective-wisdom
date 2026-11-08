# CW-181: Nest each agent Gantt chart under its status card in the dashboard

**Status:** Shipped
**Shipped:** in PR #184, as specified
**Ticket:** [#181](https://github.com/collective-wisdom-org/collective-wisdom/issues/181)
**Related:** CW-178 (#178), which decides which sessions get a chart at all. It is in spec at the same time and touches the same files.

## Goals

- A status card whose ticket has one or more agent sessions shows them inside the card, collapsed, with a control to open them.
- An opened chart stays open through the 1-second redraw and the 5-second poll.
- Sessions that belong to no card (the Chief of Staff, the root checkout, a worktree of a ticket not on the board) stay in the "Agents" list.

## Today

Facts from `main` at `d2d3bce`.

- `page/app.js` `renderStatus` draws one `li.ticket` card per row; `renderGantt` draws one `section.session` per snapshot into `#gantt` under the "Agents" heading.
- `poll` (every 5s) rebuilds `#status` only when `JSON.stringify(last.status)` changed; `draw` (every 1s) rebuilds all of `#gantt`.
- `api.ts` `buildApi` returns `status` and `gantt` as two unrelated lists.
- A snapshot's `cwd` is the session's start folder: a worktree path such as `~/.t3/worktrees/collective-wisdom/t3-7b0177e4`, the root checkout, or a folder under one of them. T3 worktree folder names carry no ticket id, so the id can't come from `cwd` alone.
- A ticket in `.agent-team/state.json` has `branch` (`feat/cw-181-nest-gantt-under-card`) once the Chief of Staff starts it; `cos_state.py` makes it optional.
- `git worktree list --porcelain` in the root checkout gives each worktree's path and branch.

## Builds

### 1. Match a session to a ticket (`server.ts`, `api.ts`)

- `server.ts` reads `git -C <root> worktree list --porcelain` with `execFile` (no shell, 5-second timeout) and parses it into `{ path, branch }` pairs (`branch refs/heads/<name>`; detached worktrees are skipped). The read runs in the background and is cached for 30 seconds, so `/api` never waits on git; the first poll after start-up may show every chart under "Agents". A failed read keeps the last good list.
- `buildApi` takes two new inputs: `worktrees: { path: string; branch: string }[]` and `prefix: string | null` (already parsed by `prefixFromProject`).
- For each snapshot:
  1. Find the worktree whose `path` equals `cwd` or is a parent folder of it (`cwd` starts with `path + '/'`). The longest path wins, so a nested `.worktrees/<name>` beats the root checkout.
  2. Take that worktree's branch. The ticket is the board ticket whose state `branch` equals it. If none does and `prefix` is set, a branch of the form `feat/<prefix in lower case>-<N>-...` names `<PREFIX>-<N>`, used if that ticket is on the board.
  3. A matched snapshot goes on that row as `row.gantt` (a list, oldest `updatedAt` first, since spec and build may be separate sessions). An unmatched one stays in the top-level `gantt` list.
- "On the board" means a row `groupTickets` returns. A session whose ticket isn't shown stays under "Agents".

### 2. Nested render (`app.js`, `index.html`)

- `renderStatus(groups, open)` takes a set of open ticket ids. A row with a non-empty `gantt` gets, below its next line:

  ```html
  <details class="chart" data-ticket="CW-181" [open]>
    <summary>Agents <span class="pill">2</span></summary>
    <div class="chart-body" data-ticket="CW-181"></div>
  </details>
  ```

  The body starts empty; `draw` fills it.
- `draw` (every 1s) fills each `.chart-body` with `renderGantt(row.gantt, now)` and `#gantt` with the unmatched list, writing `innerHTML` of the body only. The `<details>` element is never replaced by `draw`, so its open state holds.
- `poll` compares the status with the `gantt` lists replaced by their session ids, so new snapshot numbers don't rebuild the cards. When the cards do rebuild (a stage change, a new session), it reads which `details.chart` are open first and passes them to `renderStatus`, so they reopen.
- The session `h3` inside a card keeps the path and total; the stale styling stays per session. CSS: the `details` gets a small top margin and a pointer on `summary`; the nested `.session` drops its outer margin. The chart keeps its container query, so in a narrow card it uses the stacked rows from CW-175.
- With every session matched, "Agents" shows the existing quiet line `No sessions yet`.

### 3. Tests and proof

- `api.test.ts`: one table-driven test of the match: `cwd` equal to a worktree; `cwd` under it; nested worktree beats root; branch matched through state `branch`; branch matched through the `feat/cw-N-` fallback; root checkout on `main` stays unmatched; a branch of a ticket not on the board stays unmatched.
- `page/app.test.js`: one test of the nested render: a row with `gantt` gets a `details.chart` with the count, closed by default and `open` when its id is in the set; a row without `gantt` gets none.
- The `git worktree list` parser is a pure `parseWorktrees(text)` export in `api.ts`; the same api test table feeds it porcelain text, including a detached worktree that must be skipped.
- Proof: a screenshot of the dashboard on this machine's state with one card opened, and a browser check that the opened `details` is still open after 6 seconds.

## Leaves out

- Which sessions get a chart at all (CW-178).
- The in-session `agent-gantt` pane.
- Remembering open charts across a page reload.
- Any change to the snapshot format or the `agent-gantt` hook.

## Calls I made

- **The match goes through `git worktree list`, not `cwd`.** T3 worktree folders are named `t3-<hash>`, so the ticket id isn't in `cwd`. The dashboard server now runs one `git` command every 30 seconds in the root checkout.
- **State `branch` first, branch-name pattern second.** The pattern covers tickets started before `branch` was written to state.
- **One `details` per card holding every session of that ticket**, not one per session. Spec and build can be separate sessions.
- **Charts of tickets not on the board stay under "Agents"**, rather than being hidden.
- **The first poll after start-up may show every chart under "Agents"** until the background git read lands (a second or so).
- **Open state lives in the page only** and is lost on reload.
- **The api test table also covers the worktree list parser** rather than a separate test.
- CW-178 changes the same files; this change keeps its logic in a new match step in `buildApi` so the two rebase cleanly.

## Touches

None of these: data, money, auth, user email, migrations. The dashboard server runs `git worktree list` in the root checkout (read only).
