# CW-191: Split the Gantt main row into task chunks, show model and harness per row, and leave out waiting time

**Status:** Shipped
**Shipped:** in PR #194, with differences: [as-built](../as-built/2026-11-08-cw-191-gantt-task-chunks-as-built.md)
**Ticket:** [#191](https://github.com/collective-wisdom-org/collective-wisdom/issues/191)
**Related:** CW-188 (#188, dashboard header badges) merged and edited `page/app.js` and `page/index.html` too. This change stays inside `renderGantt()` and the `.grow` chart CSS, so the merge with it was small. CW-187 (#187) merged. History mode (#98) and opening a row's transcript (#97) stay out.

## Goals

- The `main` agent's time shows as one row per task it worked on, each named after the task, instead of one block from session start to now.
- Every row says which model did the work and which harness it ran on.
- A bar covers only working time. Waiting for a subagent, a background command or the user is a gap.
- The "kids" count is gone from the dashboard and the terminal pane.

## Today

Facts from `main` at `2b797f0`.

- `mods/agent-gantt/hooks/register.tsx` keeps one `AgentRecord` per agent in the `records` atom (shape `records-1`). `ensureMain()` makes the `main` record once with `end: null`, which never changes. Subagent records start at `agent.spawn`; `refresh()` stamps `end` from `last` once `$.agent.list()` stops listing them as active. `turn.complete` sums `usage` per `usage.model` with `addUsage()`.
- The mod hooks `session.start`, `command.run`, `agent.spawn`, `turn.complete` and `ui.render`. It does not hook `prompt.submit`, `turn.start` or `tool.call`.
- The engine gives what the change needs. `prompt.submit` carries the typed `text` and `isMeta` (set on a prompt the person did not type). `turn.start` and `turn.complete` carry `agentId`, absent on the main loop. `turn.complete.usage.model` is the model id. `tool.call` carries `tool`, the tool's arguments and the loop's `agentId`; `next(e)` resolves when the tool has answered.
- `rows.ts` `buildRows()` walks records depth first: `main` at depth 0, its subagents at depth 1. Each `Row` has `id, depth, name, repo, start, end, tokens, cost, childCount`.
- `snapshot.ts` `buildSnapshot()` writes `{ sessionId, cwd, updatedAt, total, rows }` to `<root>/.agent-team/gantt/<session>.json`.
- `agent-team/scripts/dashboard/api.ts` `cleanRow()` copies each row field the page reads (`childCount` included). `cleanSnapshot()` calls a session stale when it is over 30 seconds old and a row other than `main` still has `end: null`.
- `page/app.js` `renderGantt()` draws one `.bar` per row from `start` to `end` (or now), a `kids` cell, and a `Kids` header. `index.html` has `.grow .kids` CSS (the ` kids` suffix and the narrow layout order).
- The terminal pane prints a `ch` column with the same count.
- Nothing names the harness. Every snapshot comes from this mod, so every row ran on Claude Code. T3 Code starts Claude Code with `CLAUDE_CODE_ENTRYPOINT=sdk-ts` and sets `T3CODE_THREAD_ID`; a terminal session has `CLAUDE_CODE_ENTRYPOINT=cli` and no `T3CODE_THREAD_ID`.

## Builds

### 1. Record working time and tasks (`mods/agent-gantt/hooks/timeline.ts`, `register.tsx`, `types/index.d.ts`)

New record fields, with the `records` atom shape bumped to `records-2`:

- `AgentRecord.segments: [number, number | null][]`: the agent's working spans, oldest first. The last one is open (`null` end) while the agent works.
- The `main` record gets `tasks: TaskRecord[]`, where `TaskRecord = { name: string; start: number; segments: [number, number | null][]; usage: Record<string, Tokens> }`. Subagent records have `tasks: []`.
- `AgentRecord.taskIndex: number | null`: for a subagent the main loop spawned, the index of the main task that was current at spawn (so it nests under that chunk). Null for `main`, for nested subagents and when no task existed yet.
- A new `harness` atom (a string, declared in the types contract), read once at `session.start` (see 3).

`timeline.ts` holds pure functions on records, so the rules are testable without the engine:

- `taskName(text)`: the first non-empty line of the prompt with whitespace collapsed, cut to 60 characters. T3 Code's delegate preamble line (`Act as the ... agent for this task.`) is skipped, so a team child's first chunk is named after its `TEAM MODE. Run /ship-loop for CW-N: ...` line. An empty result is `task`.
- `startTask(main, name, t)`: closes any open segment of `main` and of its current task at `t`, then appends a new task with no segments.
- `openSegment(record, t)` / `closeSegment(record, t)`: open a span on the record, and on `main` also on its current task; closing an already closed record changes nothing. With no task yet, `openSegment` on `main` first starts a task named `task`.

Hooks in `register.tsx`:

- `prompt.submit` on the main loop: after `next(e)`, a prompt without `isMeta` and not dropped starts a new task named `taskName(e.text)`. A slash command's line counts (its name is the command line).
- `turn.start`: opens a segment on the agent (`agentId`, else `main`).
- `turn.complete`: closes it, and adds `usage` both to the agent and, for `main`, to the current task.
- `tool.call` for `Agent` without `run_in_background: true`, and for `AskUserQuestion`: closes the calling agent's segment before `next(e)` and reopens it when `next(e)` resolves. These are the waits inside a turn. A background `Agent` call, a `Bash` call and every other tool count as working.
- Waits between turns (a background command, a background subagent, the user's next message) need no hook: the turn ended and its segment closed.
- `refresh()` keeps today's subagent `end` stamping. When it stamps an end it also closes the agent's open segment at the same time.

### 2. Rows (`rows.ts`)

`Row` drops `childCount` and gains:

- `kind: 'session' | 'task' | 'agent'`
- `segments: [number, number | null][]`
- `model: string | null`: the model id with the most output tokens in the row's usage, with a leading `claude-` dropped (`opus-5-5`); null with no usage.
- `harness: string | null`

`buildRows()` builds, depth first:

- depth 0: the `main` row, `kind: 'session'`, named `main`. Its segments are `main`'s, so its bar has the same gaps. `start` stays the session start and `end` stays `null`, as today. The dashboard's stale rule still looks only at agents other than `main`; it skips the task rows too. Tokens and cost are `main`'s own usage, as today; model is the session's top model.
- depth 1: one `task` row per main task, id `main:task:<index>`, named after the task. `start` is the task's start; `end` is `null` while its last segment is open, else that segment's end (or the task start when it has none). Tokens, cost and model come from the task's usage.
- under each task row, at depth 2: the subagents whose `taskIndex` is that task, sorted by start, each followed by its own subagents one level deeper. Subagents without a task index go at depth 1 after the task rows, as today.
- A subagent row's segments are its own. A subagent with no segments recorded (a run whose turns no hook saw) gets one segment from `start` to `end`, the bar it has today.
- Every row's `harness` is the session's.

The session's top model and a task's model use the same picker as the agents. With no `main` record, today's fallback (subagents at depth 1) stays.

### 3. Harness

`harness` is read once at `session.start` with `$.env.get`: `T3 Code` when `T3CODE_THREAD_ID` is set, else `Claude Code`. It is kept in its own atom, not per agent, since subagents run in the same process. Codex sessions never write a snapshot (the mod is Claude Code only), so no row says `Codex`.

### 4. Snapshot and dashboard (`snapshot.ts`, `api.ts`, `page/app.js`, `page/index.html`)

- `buildSnapshot()` already writes rows as they are, so the new fields go through without a change there. `SnapshotRow` in `api.ts` follows `Row`.
- `cleanRow()` drops `childCount` and copies `kind` (one of the three values, else `agent`), `model` and `harness` (strings cut to 40 characters, else null), and `segments`: at most 500 pairs of finite numbers, each end null or at least its start, sorted by start. A row with no valid `segments` gets `[[start, end]]`, so an old snapshot draws exactly as it does today. When `cleanSnapshot()` fills a stale or finished row's `end`, it closes that row's open segment at the same time.
- `renderGantt()`:
  - draws one `.bar` per segment inside the row's `.track`, each placed on the session's axis; an open segment runs to now and takes the `running` class when the session is not stale. Each bar keeps the 0.5% minimum width.
  - drops the `kids` cell and the `Kids` header, and adds `Model` and `Harness` cells in `.meta`, after Tokens. A null value shows `–`.
  - keeps `start`, `end`, tokens and cost cells as they are.
- `index.html`: `.grow .kids` rules go; `.grow .model` and `.grow .harness` join the grid and the narrow-layout `order` list. The grid gets two columns in place of one.

### 5. Terminal pane (`register.tsx`, `format.ts`)

- The `ch` column goes. A `model` column (10 wide) takes its place; the harness shows once in the footer (`Session total $1.23 · T3 Code`), since every row in one pane has the same harness.
- `format.ts` gets `bars(segments, t0, t1, width)`: spaces with a block run per segment, each at least one cell. `bar()` stays as the one-segment case.

### 6. Tests and proof

- `timeline.test.ts` (new) and `rows.test.ts`: one table-driven test of the timeline and rows. Cases: a main timeline with two prompts and a wait in between gives two task rows and no bar over the wait; a foreground `Agent` call leaves a gap in the task's segments and a background one does not; a subagent spawned in task 2 nests under task 2 and carries its own model; the model is the one with the most output tokens; `taskName` skips the T3 preamble line; no row has `childCount`.
- `api.test.ts` and `page/app.test.js`: one test each. `cleanRow` passes the new fields, rejects bad segments, and turns an old row (no `segments`, `model`, `harness`; with `childCount`) into one segment and dashes; `renderGantt` draws one bar per segment, no `Kids` header or `kids` cell, and the model and harness cells.
- Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the pytest suite.
- Proof: load the mod in a real session (`--plugin-dir mods/agent-gantt`), send two prompts with a foreground subagent in one, and read the snapshot file and the dashboard chart: the `main` bar has gaps, there are two task rows, and the subagent row shows its model. If that check can't run from a child session, the PR lists it under Not proven.

## Leaves out

- History mode from saved transcripts (#98) and opening a row's transcript (#97).
- The CW-187 Merged list and the CW-188 header badges.
- Rows for Codex sessions, or any harness value other than the two above.
- Splitting a task on anything but a new user prompt (skills, todo items, ship-loop phases).
- Counting a long foreground `Bash` call, a permission prompt or an MCP wait tool (`t3_thread_wait`) as waiting. Only `Agent` in the foreground and `AskUserQuestion` are.
- Keeping records across the shape bump. After the mod updates, a running session starts its records fresh at the next event.
- Any change to the stale rule, the session-to-ticket match or the Merged list.

## Calls I made

- **A task is one user prompt.** Each prompt the person (or the Chief of Staff relay) sends starts a new chunk; wake-ups for a background command or subagent and continuation turns stay in the current chunk. For a team child that gives about one chunk per phase message: spec, build, merge. Splitting on skills or todo items was the other option; it is noisier and depends on the agent using them.
- **The chunk name is the prompt's first line, cut to 60 characters,** with T3 Code's `Act as the ... agent for this task.` preamble line skipped. No model call writes a summary.
- **The `main` row stays as a depth-0 session row** with the gapped bar, and the chunks sit under it at depth 1. Its `end` stays `null`, and `cleanSnapshot()` skips it and the task rows when it decides a session is working, so the stale rule keeps its meaning.
- **Subagents nest under the chunk they were spawned in** (depth 2), not directly under `main`. Subagents the mod can't place stay at depth 1.
- **Harness is `T3 Code` or `Claude Code`,** from `T3CODE_THREAD_ID`. The mod only runs in Claude Code, so there is nothing else to tell apart.
- **Harness shows once in the terminal pane's footer,** not per row, for width. The dashboard shows it per row as the ticket asks.
- **Waits inside a turn are a foreground `Agent` call and `AskUserQuestion`.** A long `Bash` or test run counts as working.
- **The model id drops its `claude-` prefix** in rows (`opus-5-5`), so the column stays narrow.
- **The `records` atom shape goes to `records-2`.** A session that is running when the mod updates loses its earlier rows and starts again from the next event.
- **`cleanRow()` caps segments at 500 per row** so a damaged or huge snapshot can't stall the page.
- **The task description travels as the row's `name`,** with `kind` telling task rows from agent rows, instead of a separate description field.

## Touches

None of these: data, money, auth, user email, migrations. The mod reads one more environment variable (`T3CODE_THREAD_ID`) and writes the same snapshot file with more fields.
