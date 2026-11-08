# CW-225: Show only a task's own work on its gantt row, and add bar tooltips

**Status:** Shipped
**Shipped:** in PR #228, as specified
**Ticket:** [#225](https://github.com/collective-wisdom-org/collective-wisdom/issues/225)
**Related:** CW-216 (waterfall by task, PR #218), CW-219 (task names, PR #221).

## Goal

A task row on the dashboard gantt is green only while the task itself works, not while it waits on a subagent. Hovering a bar says what that bar is.

## Today

Facts from `main` at `5b800cd`.

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` draws a task row from `const all = [...i.spans, ...i.kids.flatMap((k) => k.spans)]`, so the task's bars and duration are the union of its own spans and every subagent's.
- The task's own spans already leave out the time it waits on a tool call. `createWaits` in `mods/agent-gantt/hooks/timeline.ts` closes the open span when a wait begins and reopens it when the last overlapping wait ends. A foreground subagent is a tool call, so `i.spans` alone is the task's working time. No data change is needed.
- The axis (`active`) is the union of every span, task and subagent. The Total row's duration is that union's length.
- Hover text exists only per row: `rowTitle` sets a `title` on the `.grow` div. The `.bar` spans from `bars()` have no `title`.
- The `app.test.js` case "a task row includes its subagents once even when they run in parallel" expects the old behaviour (`t|3m 00s|$1.75`).

## Design

1. **Own spans on the task row.** The task row passes `i.spans` to `line()` instead of `all`. Its bars and its duration come from its own spans only. Subagent rows are unchanged. The `active` axis and the Total row are unchanged, so bars line up as before.
2. **Cost stays.** The task row's cost is still `sumCost([i.r.cost, ...kids])`, and the Total sums the same. Out of scope per the ticket.
3. **Bar tooltip.** `bars()` takes the row and gives each `.bar` a `title`, escaped with `esc`:

   ```
   <name>
   <start> to <end> · <duration> · <model>
   ```

   - `<start>` and `<end>` use `clock()`, as `rowTitle` does. A bar that is open and not stale reads `<start>, running` in place of `<start> to <end>` (the same test that gives the bar its `running` class).
   - `<duration>` is the merged bar's length, from `duration()`.
   - `<model>` is the row's `r.model`; it is left out when empty, as in `rowTitle`.
   - A bar is one merged span from `union()`, so the tooltip describes what is drawn.
   - Tokens, cost and harness are per row, not per span, so they stay in the row's hover text and are not on the bar. No new data fields.
   - The bar's `title` sits inside the row's, so the browser shows the bar's text over a bar and the row's text elsewhere on the row.

## Tests

In `agent-team/scripts/dashboard/page/app.test.js`:

- Change the parallel-subagent case to the new behaviour: the task row's duration is its own `2m 00s`, its cost is still `$1.75`, the subagent rows and the Total (`3m 00s`) are as before. Rename it to say so.
- Add one case for the bar tooltip: a row whose name has markup and a model, one closed span and one running span, checking the escaped title text of both bars.

`node --test agent-team/scripts/dashboard/page/app.test.js` passes, and so does the full `node --test` line from `AGENTS.md` § Workflow, since the PR touches `agent-team/scripts/dashboard/`.

## Non-goals

- The task row's cost (still includes its subagents).
- Any change to the data the mod collects or the snapshot shape.
- A lighter shade on the task row for the time it waits on a subagent (see Calls I made).

## Calls I made

- **No "waiting" shade.** The ticket allows it if simple. It needs interval subtraction (subagent spans minus own spans), a new bar class and CSS, and its own tooltip wording. That is more than the fix needs, so it is left out; it can be its own ticket.
- **The task row's duration is its own working time**, so it can be shorter than its subagents' time and the rows no longer add up to the Total. The Total still shows the union.
- **Bar tooltip shows the merged bar**, not each raw segment: spans that touch or overlap are one bar and one tooltip.
- **A running bar on a stale session reads as finished** (`<start> to <end>`, ending at the session's last update), matching how the bar is drawn (no `running` class) and how `rowTitle` reads.
- **Model only, no tokens or cost on the bar**, since those are per row. The row hover text keeps them.
- **The row's `title` stays** on the `.grow` div so the name column and gaps still show the row details.
