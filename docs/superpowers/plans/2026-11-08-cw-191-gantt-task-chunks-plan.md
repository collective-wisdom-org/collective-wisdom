# CW-191 plan: Gantt task chunks, model and harness, no wait time

Spec: `docs/superpowers/specs/2026-11-08-cw-191-gantt-task-chunks-design.md`. Tests per `AGENTS.md` § Testing: one table-driven test per rule. The mod side (Tasks 1, 2) and the dashboard side (Task 3) are built in parallel; they meet at the row fields in the spec's § 2.

## Task 1: timeline, rows and types (mod)

- `mods/agent-gantt/types/index.d.ts`: `Segment`, `TaskRecord`; `AgentRecord` gains `segments`, `tasks`, `taskIndex`; `PluginState` gains the `harness` atom.
- New `hooks/timeline.ts`, pure: `taskName`, `startTask`, `openSegment`, `closeSegment` (and `isWorking`).
- `hooks/rows.ts`: `Row` drops `childCount`, gains `kind`, `segments`, `model`, `harness`; `buildRows` takes a `harness` argument and builds the session row, one row per task, and subagents nested under their task.
- `hooks/format.ts`: `bars(segments, t0, t1, width)`; `bar()` calls it.
- New `hooks/timeline.test.ts`, updated `rows.test.ts` and `snapshot.test.ts`: two prompts and a wait, foreground and background gaps, subagent nesting with its own model, top model by output tokens, `taskName` preamble skip, no `childCount`.

## Task 2: hooks and terminal pane (mod)

- `hooks/register.tsx`: `records` shape `records-2`; `harness` atom set at `session.start` from `T3CODE_THREAD_ID`; hooks `prompt.submit`, `turn.start`, `turn.complete`, and `tool.call` for `Agent` (foreground) and `AskUserQuestion`; `taskIndex` set at `agent.spawn`; `refresh()` closes the open segment when it stamps an end.
- Pane: the `ch` column becomes a 10 wide `model` column, the bar is `bars(row.segments, ...)`, the footer reads `Session total $1.23 · T3 Code`.
- Bump `mods/agent-gantt/.claude-plugin/plugin.json` to 0.1.4.

## Task 3: dashboard (other implementer)

- `agent-team/scripts/dashboard/api.ts` `cleanRow` and `cleanSnapshot`; `page/app.js` `renderGantt`; `page/index.html` CSS; `api.test.ts` and `page/app.test.js`.

## Task 4: docs

- Search README, `AGENTS.md` and the mod docs for the `kids` count and the Gantt columns. None name them today, so nothing to change; older specs and plans are history.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, `claude plugin validate mods/agent-gantt`, and `python3 -I -m pytest -q agent-team/scripts`. Then load the mod with `--plugin-dir mods/agent-gantt` for the proof in spec § 6, or list it under Not proven.
