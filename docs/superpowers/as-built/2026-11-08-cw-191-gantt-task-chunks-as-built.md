# As-built: Split the Gantt main row into task chunks, show model and harness, leave out waiting time

**Shipped:** in PR #194
**Ticket:** CW-191
**Spec:** [2026-11-08-cw-191-gantt-task-chunks-design.md](../specs/2026-11-08-cw-191-gantt-task-chunks-design.md)

## Differs from the spec

- The spec pauses a task only for an `Agent` call without `run_in_background: true`. Shipped: every `Agent` call and `AskUserQuestion` pauses the caller's span for as long as the tool call blocks. The engine's default for `Agent` is background, which returns at once, so a background spawn leaves no visible gap. Parallel calls are counted per agent, so the span reopens when the last one returns.
- A prompt that is queued behind a running turn, or delivered by a task notification, does not start a task. The spec starts one for every prompt that is not meta.
- The first prompt of a session renames the placeholder task that `turn.start` made, instead of adding a second one.
- A task with no working span (a slash command that starts no turn) gets no row, and a subagent spawned in such a task sits at depth 1.
- `cleanRow()` keeps the last 500 segments, not the first 500, and the mod keeps at most the last 500 per list.
- A subagent record starts with an open span at `agent.spawn`, since its `turn.start` can come before the record exists, and a span reopened after a wait stays closed when a `turn.complete` or end stamp landed during the wait.
- When no agent is working, `cleanSnapshot()` closes the open task rows as well as `main`, at `updatedAt`.
- The harness is also read in `ensureMain`, not only at `session.start`.
