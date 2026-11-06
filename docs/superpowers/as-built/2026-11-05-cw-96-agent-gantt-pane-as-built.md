# As-built: A live Gantt and cost pane for agents, as a Claude Code mod

**Shipped:** in PR #149
**Ticket:** CW-96
**Spec:** [2026-11-05-cw-96-agent-gantt-pane-design.md](../specs/2026-11-05-cw-96-agent-gantt-pane-design.md)

## Differs from the spec

- The spec gives `buildRows(records, agentList, prices, now)`. It shipped as `buildRows(records, agents, prices)`: the builder never read `now`, since `end` is null while an agent runs and the pane draws the bar to the current time.
- Tokens are kept per model id, not per family. Cost still matches by family, as `agent_usage.py` does. One unknown model among an agent's models makes that row's cost `–`.
- An agent counts as finished when `$.agent.list()` no longer shows it as `pending`, `running` or `waiting`, not just `running`, so an agent waiting on a permission doesn't show an end time.
- The end time is the agent's last `turn.complete`, stamped on a later `turn.complete` or on the 5 second tick, because the last `turn.complete` can arrive before the status changes.
- Row names prefer the name from `$.agent.list()` over the spawn's `description`.
- `plugin.json` carries an `author`, and a small `format.ts` holds the pane's text helpers.
- On a narrow pane (under about 76 columns) each bar sits on its own line.
