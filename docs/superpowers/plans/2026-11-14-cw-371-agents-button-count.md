# CW-371 plan: Agents button count

Spec: `docs/superpowers/specs/2026-11-14-cw-371-agents-button-count-design.md`

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, then `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: count and summary (`app.js`)

- `taskCount` returns `ganttTasks(sessions, 0).reduce((n, i) => n + 1 + i.kids.length, 0)`; update its doc comment.
- `ganttSummary` returns `{ ms, cost }` (no `agents`); update its comment.
- `summaryLine` joins only duration and cost; update its comment.

## Task 2: tests (`app.test.js`)

- Update the footer summary test (`{ ms, cost }`, `3m 00s · $1.50`).
- Add one table test: a Gantt of 2 tasks and 3 subagents gives `Agents 5` through `renderStatus`, `renderMerged` and `renderChief` (project manager row); an empty Gantt gives a disabled `Agents 0`.

## Task 3: README

- Dashboard paragraph: `Agents` count of tasks and their subagents; summary example `41m 05s · $2.10`.
