# CW-216: Redesign the agent gantt as a waterfall by task, with active time only

**Status:** Shipped
**Shipped:** in PR #218, with differences: [as-built](../as-built/2026-11-08-cw-216-gantt-waterfall-as-built.md)
**Ticket:** [#216](https://github.com/collective-wisdom-org/collective-wisdom/issues/216)
**Related:** CW-181 (gantt under the card), CW-191 (task chunks, waiting time), CW-213 (gantt on merged PRs, PR #214).

## Goal

The "Agents" chart under a status card and under a merged PR row answers three questions at a glance: what work was done on this ticket, how long the agents actually worked on each piece, and what each piece cost. Every piece of work appears once, waiting on a person takes no space and no time, and the costs add up to the total on the chart.

## Today

Facts from `main` at `73cd73d`.

- `buildRows` in `mods/agent-gantt/hooks/rows.ts` emits, per session: one `session` row for `main` (depth 0) with all of main's spans, tokens and cost; one `task` row per prompt (depth 1) with that prompt's share; one `agent` row per subagent, under the task current at its spawn (depth 2 and down), or at depth 1 when it can't be placed.
- The `session` row and the `task` rows split the same main-loop work two ways. With one prompt, the two rows carry the same spans and the same cost, so the chart shows that work twice.
- `taskName` in `mods/agent-gantt/hooks/timeline.ts` skips T3 Code's first line with `PREAMBLE = /^Act as the .* agent for this task\.?$/i`. The child prompt `Act as the implementation sub-agent for this task.` does not match (the pattern wants a space before `agent`), so every team child's task is named after the preamble.
- `pauseWhile` in `register.tsx` closes the agent's span while an `AskUserQuestion` or a foreground `Agent` call is blocked. A permission prompt and a plan approval (`ExitPlanMode`) are counted as working time.
- `writeSnapshot` stores `total` from `$.session.usage().cost.usd`, the engine's own figure. Row costs are priced by the mod from `~/.collective-wisdom/scripts/prices.json`, cache writes at the 5 minute rate. Nothing reconciles the two.
- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` draws each session as its own box: a header with the worktree path and the session `total`, then one grid row per snapshot row (name, cost, a meta line with repo, clock range, tokens, model and harness, then the bar). Bars are placed on wall-clock time from the session's earliest start to its latest end. The `Agents` pill counts sessions.
- The engine reports a permission ask before it is answered: the `tool.check` event resolves to `{ decision: 'ask' }`, and its input carries `approver: 'host' | 'person'` (`host` is a host's permission callback, as in T3 Code; `person` is the terminal dialog) and the call's `tool_use_id`. The dialog and the tool then run inside that call's `tool.call` `next(e)`.

## Design critique of the current chart

Read as a designer would, with the CW-213 card as the example (main and its one task at $1.16 each, four subagents at $1.27, a $2.16 total).

1. **It is organized by plumbing, not by work.** The top level is a session (a worktree path), which is how the mod collects data, not how a person thinks about a ticket. A ticket that ran a spec child and a build child shows two boxes with near-identical paths, and you have to read the paths to tell them apart.
2. **The same work is drawn twice.** The `main` row is the sum of its task rows. With one task the two rows are identical, and your eye adds both. The doubled $1.16 is the first thing a reader sees and it is wrong.
3. **The numbers don't add up, and nothing says so.** $1.16 + $1.16 + $1.27 is $3.59; the header says $2.16. Even without the duplicate, $2.43 against $2.16 leaves the reader unsure which figure to trust.
4. **Wall-clock axis, so waiting dominates.** A ticket that waited four hours for a spec approval between a 10 minute spec and a 30 minute build draws two slivers at the far edges of the track. The longest thing on the chart is the time nobody worked. Duration is not shown as a number at all; you read it off a clock range (`14:02 to 14:31`) and subtract.
5. **Names are the preamble.** Every team child task is called "Act as the implementation sub-agent for this task.", so the one word that should say what the task was says nothing.
6. **Too much meta per row.** Repo, clock range, tokens, model and harness sit on every row in the same weight. On a ticket the repo and harness are the same on every row. The facts the ticket asks for (time, cost) compete with them.
7. **The pill counts the wrong thing.** `Agents 2` means two sessions, which the reader can't act on.

What works and stays: the collapsible `Agents` section in both places, bars that show a running task, the stale marker, indenting subagents under the task that started them.

## Proposed layout: one waterfall per ticket

One chart per ticket, not one box per session. Rows are tasks of work in the order they started, across all of the ticket's sessions. The horizontal axis is **active time**: every moment when no agent of the ticket was working is cut out, so the bars run end to end like a waterfall and the track's full width is the ticket's total working time.

```
Agents  3 tasks · 43m active · $2.43
┌───────────────────────────────────────────────────────────────────────────────┐
│ Run /ship-loop for CW-213: Show the agent gantt on merged…   ▇▇▇▇           │  9m 12s   $0.61 │
│   └ Explore: read the dashboard code                              ▇▇        │  3m 05s   $0.22 │
│ CHIEF OF STAFF: approved the spec. Build it.                       ▇▇▇▇▇▇▇▇▇ │ 27m 40s   $1.58 │
│   └ implementer: build history.ts                                  ▇▇▇▇▇    │ 14m 02s   $0.71 │
│   └ security-reviewer: review PR #214                                   ▇▇  │  4m 10s   $0.31 │
│ CHIEF OF STAFF: approved the merge.                                       ▇ │  6m 20s   $0.24 │
├───────────────────────────────────────────────────────────────────────────────┤
│ Total                                                                          │ 43m 12s   $2.43 │
│ Claude Code reports $2.16 for these sessions. Row costs use prices.json.                         │
└───────────────────────────────────────────────────────────────────────────────┘
```

(Names and numbers are illustrative.)

Reasoning, mapped to the critique:

- **One row per task, in start order** (1, 7). A reader scans down a list of what was done. Session boundaries are not drawn; a session's harness and worktree go into the row's hover title with the model and tokens (6). The pill becomes the count of tasks.
- **Each row carries its subtotal** (2, 3). A task row's time and cost include its subagents; a subagent row is indented and muted, showing its own share. Only the task rows sum to the total, which is drawn on the last line and is their sum, so the chart adds up by construction.
- **Active time, as a number and as the axis** (4). The right-hand column is the row's active duration (`9m 12s`), the length of the union of its working spans, so parallel subagents are not double-counted. The axis drops every gap where nothing worked, so a four hour approval wait takes zero pixels.
- **The engine's figure is a note, not a competing total** (3). When the engine's session totals, summed, differ from the row total by a cent or more, one line under the total says so. It is never presented as the total.
- **Names say what the task was** (5). The preamble fix means a team child's task is named after its real first line, such as `TEAM MODE. Run /ship-loop for CW-216: …` with the leading `TEAM MODE.` dropped.
- **Two numbers, one bar.** Name on the left, bar in the middle, time and cost in fixed right-hand columns with tabular numbers, so the eye can run down either column. On a narrow card the bar wraps under the name, as the grid does today.

## Builds

1. **Mod: no row twice.** `buildRows` stops emitting the `session` row. When main's own cost or tokens exceed the sum of its task rows (usage that landed before any task opened), it emits one more depth 1 task row named `outside a task` with the difference, so nothing is lost. The pane in Claude Code reads the same rows, so it loses the duplicate too; its drawing is otherwise unchanged.
2. **Mod: the preamble matches `sub-agent`.** `PREAMBLE` matches `Act as the … agent for this task.`, `… sub-agent …` and `… subagent …`. `taskName` also drops a leading `TEAM MODE.` from the line it keeps.
3. **Mod: approval waits are not working time.**
   - A `tool.check` hook awaits `next(e)`. When the verdict is `ask`, the input has an `approver` and a `tool_use_id`, the agent's span closes at that moment and the call is marked as waiting.
   - A `tool.call` hook on every tool reopens the span when a marked call's `next(e)` settles, under the same counting rules as `pauseWhile` (overlapping waits, an agent that finished during the wait stays closed).
   - `ExitPlanMode` joins `AskUserQuestion` and `Agent` in the `pauseWhile` list: its call is a plan approval.
   - The wait counting moves out of `register.tsx` into a pure helper in `timeline.ts` so the rule is testable with a fake clock.
4. **Page: `renderGantt` draws the waterfall** described above, from the sessions it gets today, in both places (status card and merged row).
   - It merges all sessions' rows into one list of top-level items: each `task` row and each depth 1 `agent` row, with the rows nested under it. Old snapshots and stored history still carry a `session` row; the page drops it when its session has task rows and treats it as a task otherwise.
   - Active axis: the union of all working spans of all rows; a time maps to the active milliseconds before it. A running span ends at `now` (at `updatedAt` for a stale session).
   - Each top-level row shows name, bar, active duration (union of its own and its descendants' spans) and cost (own plus descendants; a dash when any is unknown). Nested rows show their own duration and cost, indented and muted. Model, tokens, harness and worktree move into the row's `title`.
   - The last line shows total active time and the sum of the top-level costs. When every session has an engine `total` and their sum differs from the row sum by $0.01 or more, a note follows: `Claude Code reports $X for these sessions. Row costs use prices.json.`
   - A stale session's rows keep the stale styling; the `stale` pill moves to each of its rows' names.
   - The `Agents` pill counts top-level tasks, which needs the same merge, so the pill and the chart share one helper.
5. **Why the costs differ.** The build compares one real snapshot's row costs with its engine `total` and writes the cause (cache write rate, usage before the mod saw the session, or something else) in the as-built. If the cause is a mod pricing bug, it is fixed here; otherwise the note above is how the page handles it.
6. **Tests**, per `AGENTS.md` § Testing.
   - `timeline.test.ts`: one table for `taskName` (`agent`, `sub-agent`, `subagent` preambles skipped, `TEAM MODE.` dropped); one table for the wait helper with a fake clock (a permission ask, a plan approval, overlapping waits, an agent that ends mid-wait), each asserting the record's spans have no span over the wait.
   - `rows.test.ts`: no `session` row; one task gives one row carrying main's work once; main usage outside any task gives the `outside a task` row.
   - `app.test.js`: one table for `renderGantt`: two sessions merge into one list in start order; an idle gap between tasks takes no width; a task row's time and cost include its subagents and parallel subagents count once; the total is the sum of top-level rows; the note appears only when engine totals differ; an old snapshot's `session` row is not drawn when tasks exist; the pill counts tasks.

## Leaves out

- How the team runs tickets or how approvals work.
- Time between turns. A child that stops at `BUILD READY` and waits for the next message has no open span already; the active axis just stops it taking space.
- Rewriting stored history. Old sessions draw through the same page rules, with their recorded spans (which may include old approval waits).
- The pane's layout in Claude Code, beyond losing the duplicate row.
- The spend ledger and the merged row's spend figure (CW-209).

## Calls I made

- **The ticket's sessions merge into one chart.** The ticket names "not per thread or session"; I read it as no session boxes at all, with the worktree in each row's hover title.
- **The axis is active time, not wall clock.** Clock times are gone from the rows (they stay in the hover title). Without this, waits still take most of the width even when no bar is drawn for them.
- **Task rows carry subtotals, subagent rows are a breakdown.** The alternative, every row showing only its own share, makes all rows sum but hides what a task cost as a whole.
- **The total is the row sum; the engine's figure becomes a note.** The ticket allows either; a total that matches its rows is the one a reader can check.
- **An `ask` counts as waiting from the check until the call finishes,** so the tool's own run time after approval is counted as waiting too. The engine gives no event between the dialog closing and the tool starting. Most approved calls are short commands.
- **An `ask` with no `approver` is working time,** since nobody is asked. An `ask` the auto mode classifier settles has an approver and its few seconds are counted as waiting.
- **Task names stay the prompt's first real line,** with `TEAM MODE.` dropped. Mapping known team prompts to phase names (Spec, Build, Merge) would tie the mod to the ship loop's wording.
- **`outside a task` row** instead of dropping main's usage that has no task, so the total keeps every dollar.
- **The pane changes only through `buildRows`.** The ticket keeps the pane out of scope; sharing `buildRows` means it loses the duplicate for free.

## Not proven until a real run

- That T3 Code's approvals reach the engine as an `ask` with `approver: 'host'`. The types say so; the build's tests use a fake event. If they don't, an approval wait in a T3 session is still counted, and the as-built says so.
