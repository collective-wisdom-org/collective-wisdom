# CW-219 plan: name gantt tasks by the work

Spec: [2026-11-08-cw-219-gantt-task-names-design.md](../specs/2026-11-08-cw-219-gantt-task-names-design.md)

## Task 1: taskName with earlier names

- `mods/agent-gantt/hooks/timeline.ts`: `taskName(text, earlier: string[] = [])` per the spec § Design (preamble as a line prefix, drop `TEAM MODE.` then `CONTINUE.`, `CHIEF OF STAFF:` relay table with ticket from the newest earlier name carrying an id, 60-char cut, `task` fallback).
- `mods/agent-gantt/hooks/register.tsx`: the `prompt.submit` handler passes the names of main's tasks (`r.tasks.map(k => k.name)`) to `taskName` inside the `updateRecord` callback.
- `mods/agent-gantt/hooks/timeline.test.ts`: extend the table-driven `taskName` test with the spec § Tests cases; existing cases stay.
- `mods/agent-gantt/.claude-plugin/plugin.json`: version 0.1.6.
- Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
