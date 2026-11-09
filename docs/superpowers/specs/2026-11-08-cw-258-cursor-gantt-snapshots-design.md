# CW-258: Produce agent-gantt snapshots from Cursor threads

**Status:** Draft
**Ticket:** [#258](https://github.com/collective-wisdom-org/collective-wisdom/issues/258)
**Related:** [#253](https://github.com/collective-wisdom-org/collective-wisdom/issues/253) (Cursor rotation hook, which adds the `~/.cursor/hooks.json` merge this spec extends)

## Goal

A Cursor child thread on a worktree gets a gantt row on the dashboard: its tasks, its subagents and when each one worked, labelled `Cursor`. Cursor's hooks write the same snapshot file the `agent-gantt` mod writes for Claude Code, and `./install.sh` registers them in `~/.cursor/hooks.json` through CW-253's merge.

## Today

Facts from `main` at `cbc35dc`.

- `mods/agent-gantt/hooks/register.tsx` keeps `AgentRecord`s in mod atoms from Claude Code events (`session.start`, `prompt.submit`, `turn.start`, `turn.complete`, `agent.spawn`, waits) and, on each refresh, writes `<root checkout>/.agent-team/gantt/<session id>.json` with `buildRows` (`rows.ts`) and `buildSnapshot` (`snapshot.ts`). It writes only when the root has `docs/agents/project.md` or `.agent-team/state.json`, skips a session id that fails `snapshotName`, and skips a linked `.agent-team`, `gantt` folder or snapshot file.
- A snapshot is `{sessionId, cwd, updatedAt, total, pricing: 2, threadId, heading, rows}`. Each row has `id, depth, kind, name, repo, start, end, tokens, cost, segments, model, harness`. `harness` is `T3 Code` or `Claude Code`.
- The dashboard (`agent-team/scripts/dashboard/server.ts`) reads every `*.json` directly in `.agent-team/gantt/`. `api.ts` keeps a snapshot whose `cwd` is a worktree, ties it to a ticket by the worktree's branch, and draws its rows. Spend comes from `total` and the rows' `tokens`.
- A Cursor thread runs none of this, so it has no gantt row and no spend (`docs/compatibility.md` G9).
- `~/.collective-wisdom` links to the clone's `agent-team/`, so `mods/` is not under it. `dashboard/api.ts` already imports `../../../mods/agent-gantt/hooks/rows.ts`, which works because Node resolves the link to the clone.

### What Cursor's hooks give

From <https://cursor.com/docs/hooks>, read 2026-11-08.

- Every agent hook gets on stdin `conversation_id`, `generation_id`, `model`, `model_id`, `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`. Cursor sets `CURSOR_PROJECT_DIR` (and `CLAUDE_PROJECT_DIR`) to the workspace root. A user hook runs from `~/.cursor/`.
- The events this ticket uses, and what each adds:

| Event | Adds | Output Cursor reads |
|---|---|---|
| `sessionStart` | `session_id`, `is_background_agent`, `composer_mode` | `env`, `additional_context` (fire and forget) |
| `beforeSubmitPrompt` | `prompt`, `attachments` | `continue`, `user_message` |
| `stop` | `status` (`completed`, `aborted`, `error`), `loop_count` | `followup_message` |
| `subagentStart` | `subagent_id`, `subagent_type`, `task`, `parent_conversation_id`, `tool_call_id`, `subagent_model`, `is_parallel_worker`, `git_branch` | `permission` (a permission hook: bad JSON on exit 0 blocks the spawn) |
| `subagentStop` | `subagent_type`, `status`, `task`, `description`, `summary`, `duration_ms`, `message_count`, `tool_call_count`, `loop_count`, `modified_files`, `agent_transcript_path` | `followup_message` |
| `sessionEnd` | `session_id`, `reason`, `duration_ms`, `final_status` | none |

- Other events (`preToolUse`, `postToolUse`, shell, MCP, file, `preCompact`, `afterAgentResponse`, `afterAgentThought`) are not needed.
- When several hooks answer one event, the last `followup_message` wins. An exit code other than 0 and 2 lets the action go on.

### What `snapshot.ts` needs that Cursor does not give

| Snapshot field | From Cursor |
|---|---|
| `sessionId` | `conversation_id` |
| `cwd` | `workspace_roots[0]`, else `CURSOR_PROJECT_DIR` |
| `updatedAt`, row `start`, `end`, `segments` | No timestamps in any payload. The hook's own clock at each event; a subagent's start is also checked against `duration_ms` on stop |
| `threadId` | Not in the payload. `T3CODE_THREAD_ID` from the hook's environment when T3 Code passes it down (not proven), else null |
| `heading` | The first `beforeSubmitPrompt` `prompt`, through `pickHeading` |
| row `model` | `model` (main and tasks), `subagent_model` (subagents) |
| row `tokens`, `cost`, snapshot `total` | **Not given.** No event, and no line of Cursor's transcripts on this machine, carries token usage or cost. Rows get `tokens: 0`, `cost: null`, and `total: null` |
| Waits inside a turn (questions, permission asks) | Not given as events. A Cursor turn is one span from prompt to stop |
| Subagent id on stop | `subagentStop` has no `subagent_id`. The stop is matched to the oldest open subagent with the same `subagent_type` and `task` |

## Design

### 1. The mapping: `mods/agent-gantt/hooks/cursor.ts`

Pure functions, no file or process access, next to the code they reuse:

- `applyEvent(state, payload, now)` returns the new state. `state` is `{records: AgentRecord[], heading: {isSet, value}, model: string | null, subagentModels: Record<id, string>}`, the same records the mod keeps. It reuses `beginTask`, `taskName`, `openSegment` and `closeSegment` from `timeline.ts`:
  - any event: the `main` record is made if missing, starting at `now`, with `cwd` from the payload.
  - `beforeSubmitPrompt`: begins a task named by `taskName(prompt)` and opens a segment on `main` (`turn.start` in the mod). Sets the heading once. Keeps `model`.
  - `stop`: closes the open segment on `main` and the current task.
  - `subagentStart`: adds a record with `id` `subagent_id`, `parentId` `main`, name `task` (else `subagent_type`), an open segment from `now`, and `taskIndex` set to the current task, so it nests the way a Claude Code subagent does.
  - `subagentStop`: finds the open record (oldest with the same type and task), closes its segment and sets `end`. With no match it adds a closed record from `now - duration_ms` to `now`, so a start the hook missed still draws.
  - `sessionEnd`: closes every open segment and record.
  - an unknown event or a payload without `conversation_id`: state unchanged.
- `cursorSnapshot(state, payload, now, threadId)` returns the snapshot text: `buildRows(records, [], null, 'Cursor')`, then each row's `model` set from the kept models (the `claude-` prefix dropped as `rows.ts` does), then `buildSnapshot` with `total: null`.
- `hookOutput(event)` returns what to print: `{"permission":"allow"}` for `subagentStart`, `{"continue":true}` for `beforeSubmitPrompt`, nothing for the rest. The gantt hook never blocks, never adds a follow-up and never sets `user_message`.

### 2. The hook: `agent-team/scripts/cursor_gantt_hook.ts`

Run as `node "$HOME/.collective-wisdom/scripts/cursor_gantt_hook.ts"`. It imports `cursor.ts` and `snapshot.ts` from `../../mods/agent-gantt/hooks/` the way `dashboard/api.ts` does.

1. Reads stdin and parses it. It prints `hookOutput(event)` **first**, before any other work, so a crash later cannot block a spawn or a prompt. Any error after that is caught; it exits 0.
2. Finds the root checkout the way `register.tsx` does: `git rev-parse --path-format=absolute --git-common-dir` run in `cwd`, kept only when it ends in `/.git`, else `cwd`. Skips a root without `docs/agents/project.md` or `.agent-team/state.json`.
3. Skips a `conversation_id` that fails `snapshotName`, a linked `.agent-team`, `gantt` or `gantt/cursor` folder, and a linked target file. These are the mod's checks.
4. Takes a lock (`mkdir` of `<root>/.agent-team/gantt/cursor/<id>.lock`, retried for up to 2 seconds, removed in `finally`), so two parallel subagent hooks do not lose each other's update. A lock it cannot get within 2 seconds skips the event. A lock older than 30 seconds is removed first.
5. Reads the state from `<root>/.agent-team/gantt/cursor/<id>.json` (missing or bad: empty state), applies the event, writes the state, then writes `<root>/.agent-team/gantt/<id>.json` with `cursorSnapshot`. Both are written to a temp file in the same folder and renamed.

The state lives in a subfolder, so the dashboard, which reads only the `*.json` files directly in `gantt/`, never reads it as a snapshot. `.agent-team/` is already outside git in an app.

### 3. Registering it: extend CW-253's `cursor-hook` merge

CW-253 adds an `mpython` mode, `cursor-hook`, that merges one `stop` entry (marked by `cos_rotation_check.py`) into `~/.cursor/hooks.json`. This ticket does not add a second merge. It turns that mode's one entry into a list of `(event, command, marker)` entries and adds the gantt hook for `sessionStart`, `beforeSubmitPrompt`, `stop`, `subagentStart`, `subagentStop` and `sessionEnd`, each with the marker `cursor_gantt_hook.ts` and `timeout: 5`. Everything else is CW-253's rule, per entry:

- An event whose list already mentions the entry's marker is left alone, so a rerun adds nothing.
- New entries are appended, except the gantt `stop` entry, which goes in **before** the rotation hook's entry. Cursor keeps the last `followup_message`, and the gantt hook prints none; putting it first keeps the rotation hook last.
- The file's other keys and hooks stay. A file CW-253 calls invalid stays invalid: nothing is written, and the TODO lists every entry to add by hand.
- `install.sh` prints one `added  ~/.cursor/hooks.json (<events>)` line.

### 4. How this lands with CW-253

CW-253 merges first. This ticket's build:

1. Builds sections 1 and 2 and their tests on its own branch. They touch no file CW-253 touches.
2. Before the `install.sh` task, merges `origin/main` into the branch after CW-253 has merged, then changes CW-253's `cursor-hook` code and tests in place.
3. If CW-253 has not merged by then, stops with `BLOCKED: waiting for CW-253 to merge`. It does not copy CW-253's merge into this branch.

`docs/agents/project.md` § Security overlays already names `~/.cursor/hooks.json` once CW-253 lands. This ticket adds one sentence to it: the Cursor gantt hook writes only inside `<root checkout>/.agent-team/gantt/`, like the mod.

### 5. Docs

- `docs/compatibility.md`: the Local dashboard cell for Cursor becomes `🟡 partial: gantt rows, no spend (G9); rest untested (G3)`. G9 says Cursor threads write snapshots through Cursor hooks with timing and models but no tokens or cost, since Cursor's hooks and transcripts carry none, and that Codex and Antigravity still write none. The note on spend under the matrix names G9.
- `README.md`: the install paragraph's `~/.cursor/hooks.json` mention (from CW-253) also names the gantt hook.

### Tests

- `mods/agent-gantt/hooks/cursor.test.ts`: one table over event sequences, each checked against the rows it should give: prompt then stop (one task, one closed span); two prompts (two tasks); a subagent started and stopped inside a task (nested at depth 2, closed); a stop with no start (a closed row of `duration_ms`); two parallel subagents of one type stopped in order; `sessionEnd` with a span open; an unknown event (state unchanged). Every row checks `harness: 'Cursor'`, `tokens: 0`, `cost: null`, and the model. One table for `hookOutput` over the six events.
- `agent-team/scripts/dashboard/api.test.ts`: one case that a Cursor snapshot on a ticket's worktree reaches that ticket's `gantt`. This is the acceptance check that runs without Cursor.
- `test_install_machine.py`: CW-253's `hooks.json` table gains the gantt entries: a fresh file gets all seven entries with the gantt `stop` entry before the rotation one; a rerun adds nothing; a file with only the rotation hook gets the gantt ones added in the right order.
- No test drives `cursor_gantt_hook.ts` end to end. Its file steps are the mod's checks, run by hand once (below).

## Leaves out

- Tokens, cost and spend for Cursor threads. Cursor gives none; a later ticket could read them if Cursor adds them. The No Hands cost cap (G8) is unchanged.
- The `agent-gantt` and `status-pane` panes (G10).
- Codex and Antigravity hooks.
- Waits inside a Cursor turn (questions, permission asks): the turn is one span.
- A project-level `.cursor/hooks.json`.

## Not proven before merge

- No Cursor thread runs the hook in this PR. As in CW-253, whether T3 Code's Cursor provider loads `~/.cursor/hooks.json` and runs these six events, and passes `T3CODE_THREAD_ID` to hooks, is unproven until a Cursor child thread runs on a worktree.
- The PR runs the hook by hand once: Cursor-shaped payloads piped into `node agent-team/scripts/cursor_gantt_hook.ts` from a scratch worktree, and the dashboard's `/api` shows the row. That proves the file path, not Cursor.

## Calls I made

- **No spend for Cursor rows.** Cursor's hooks and transcripts have no token or cost field, so rows show `0` tokens and no cost, and the compatibility cell stays partial. The ticket asked for spend; it cannot be had from what Cursor sends.
- **The gantt `stop` entry goes before the rotation hook's**, so the rotation hook's follow-up is the one Cursor keeps.
- **The hook prints its answer before doing anything else**, and answers allow and continue, so a broken gantt hook can never block a subagent or a prompt.
- **`subagentStop` is matched by type and task**, since it carries no `subagent_id`. Two parallel subagents with the same type and task can swap end times; the chart is still right in count and span.
- **Harness label `Cursor`**, not `Cursor in T3 Code`, matching the ticket.
- **Node, not Python**, so the hook reuses `buildRows`, `buildSnapshot`, `pickHeading` and the timeline helpers instead of a second copy. It runs `node` from `PATH`, as the dashboard start does; with no Node, Cursor gets a non-zero exit and goes on.
- **The pure mapping lives in `mods/agent-gantt/hooks/`** beside the code it reuses, and the CI glob there runs its test. The entry script lives in `agent-team/scripts/`, so it is reachable at `~/.collective-wisdom/scripts/`.
- **Hook state in `.agent-team/gantt/cursor/`**, a folder the dashboard does not read, with a 2-second lock.
- **`threadId` from `T3CODE_THREAD_ID`** if the hook sees it, else null. A Cursor child's ticket match uses the worktree, so it does not need it.
- **`timeout: 5`** on each gantt entry, so a stuck hook does not hold a turn.
- **Order with CW-253**: this ticket waits for CW-253 to merge before its `install.sh` task, and stops `BLOCKED:` if CW-253 has not.
- The spec adds a sentence to `docs/agents/project.md` § Security overlays.
