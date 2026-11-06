# CW-96: A live Gantt and cost pane for agents, as a Claude Code mod

**Ticket:** [CW-96](https://github.com/collective-wisdom-org/collective-wisdom/issues/96)
**Status:** Shipped
**Shipped:** in PR #149, with differences: [as-built](../as-built/2026-11-05-cw-96-agent-gantt-pane-as-built.md)
**Related:** #135

## Goal

A pane beside the chat shows this session's agents as a Gantt chart. Each row is one agent with its name, repo, start, end, tokens, cost and child count, plus a bar from start to end. Children sit under their parent. The pane redraws as agents start and finish, so you can see at a glance what is running, for how long, and what it costs.

## Today

Facts from `main` at `9ad1321`, checked 2026-11-05.

- No such view exists. The Chief of Staff's idle check lists running children as text (`agent-team/.claude/skills/chief-of-staff/SKILL.md` § Lean turns).
- `agent-team/scripts/agent_usage.py` holds the list prices as a Python dict, `PRICES` (dollars per million tokens: input, output, cache read, cache write 1h, cache write 5m, keyed by model family), and `costs(model, usage)`. When a usage has no `cache_creation` split, `costs()` prices all cache writes at the 5m rate.
- `install.sh` ships only `agent-team/`, and from it only `.claude/skills`, `.claude/agents`, `scripts` and `docs/agents` (`shipped()`). Every file under `agent-team/scripts/` reaches an app at `scripts/`.
- The repo is public. It has no `.claude-plugin/` folder and no marketplace file.
- CI (`.github/workflows/ci.yml`) has two jobs, `script-tests` (pytest) and `shellcheck`. `review_scope.py --ci` skips tests only when every changed file is a docs file.
- What a mod can read, from the Claude Code types for this build:
  - `$.agent.list()` gives `AgentInfo` rows: `id`, `parentId` (absent when the main loop spawned it), `type`, `description`, `name`, `status`.
  - `agent.spawn` carries `description`, `subagentType`, `model`, `parentModel`, `parentAgentId` and `cwd`.
  - `turn.complete` carries `agentId` (absent on the main loop), `durationMs` and `usage`: `model`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`. There is no 1h/5m split of cache writes.
  - `$.session.usage()` gives the session's cost and start time.
  - `$.fs.read(path)` reads a file, relative to the session's working directory.
  - No event or list entry gives an agent's start or end time, so the mod stamps them itself.

## Design

### Where the mod lives and how it ships

> ⚠️ This answers the ticket's Open section. It is a call I made; see Calls I made.

- The mod lives at `mods/agent-gantt/` at the repo root, beside `agent-team/`, not under it. `install.sh` does not copy it and nothing about installs into apps changes.
- The repo becomes a Claude Code plugin marketplace: one new file, `.claude-plugin/marketplace.json` at the root, named `collective-wisdom`, with one entry `{ "name": "agent-gantt", "source": "./mods/agent-gantt" }`.
- A person installs it once per machine, at the user scope, so it works in every repo and T3 worktree they open:

  ```
  /plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom
  ```

  `claude plugin update agent-gantt` picks up a newer version. The README gets a short "Agent pane" section with that line, the shell form and the desktop-app steps.
- The mod's `plugin.json` carries a `version`. A PR that changes the mod bumps it; that is the only release step. Tagged agent-team releases (`tag-release.sh`) don't cover the mod.

Mod layout:

```
mods/agent-gantt/
  .claude-plugin/plugin.json
  hooks/hooks.json            { "modules": ["./register.tsx"] }
  hooks/register.tsx          hooks: spawn, turn end, pane drawing, command
  hooks/rows.ts               the row builder: pure, no engine calls
  hooks/rows.test.ts          node:test cases for the row builder
  types/index.d.ts            $.state contract
```

### Prices: one table, read by both

The ticket asks the pane to reuse `agent_usage.py`'s prices, not copy them. A TypeScript mod can't import a Python dict, so the table moves to a file both read:

- New `agent-team/scripts/prices.json`: the same numbers as `PRICES` today, keyed by family, with the five rates named (`input`, `output`, `read`, `write_1h`, `write_5m`).
- `agent_usage.py` loads `PRICES` from that file at import, into the same tuple shape, so `costs()`, `family()` and every caller are unchanged. Its tests keep passing as they are.
- The mod reads `scripts/prices.json` with `$.fs.read` at session start. That path exists in this repo, in its worktrees and in every app that installed the agent team. Where it is missing or doesn't parse, the pane shows tokens and leaves the cost column as `–`, with one line under the chart saying why.
- Cost of one call: tokens times the rates for the call's model family. Cache writes use the 5m rate, as `costs()` already does when there is no split.

### What the mod records

The mod keeps one record per agent in `$.state`, so a reload keeps them:

| Field | From |
|---|---|
| `id`, `parentId` | the agent id after `agent.spawn`'s `next(e)` resolves, and `parentAgentId` |
| `name` | `name` from `$.agent.list()` when set, else the spawn's `description` |
| `type` | `subagentType` |
| `cwd` | the spawn's `cwd`, else the session's working directory |
| `start` | clock time when `agent.spawn` resolves |
| `end` | clock time of the agent's last `turn.complete` once `$.agent.list()` no longer shows it `running` |
| `usage` | summed per model family from every `turn.complete` with that `agentId` |

The main loop gets one record too (id `main`, no parent), started when the mod loads, never ended, with its own `turn.complete` usage. Every agent the main loop spawns sits under it.

### The row builder

`rows.ts` exports `type Row` and `buildRows(records, agentList, prices, now)`. It is pure, so it can be tested without the engine.

`Row` is the contract the history ticket fills later:

```ts
type Row = {
  id: string
  depth: number          // 0 for main, 1 for its children, and so on
  name: string
  repo: string
  start: number          // ms since epoch
  end: number | null     // null while running
  tokens: number         // input + output + cache read + cache write
  cost: number | null    // dollars; null without a price table or for an unknown model family
  childCount: number
}
```

Rules:

- Order: depth first. Each parent is followed by its children, sorted by start.
- A record whose parent is unknown sits under `main`.
- `childCount` is the number of `$.agent.list()` entries whose `parentId` is this row's id (for `main`, entries with no `parentId`). It counts children listed but not yet recorded, so it matches `$.agent.list()`.
- `repo` is the repo name from `cwd`: for `~/.t3/worktrees/<repo>/<id>` it is `<repo>`, for `<root>/.worktrees/<name>` it is the folder name of `<root>`, otherwise the last path segment.
- `end` is null while the agent runs; the bar is drawn to `now`.

### The pane

- `register.tsx` opens the pane (`$.ui.open({ id: 'agent-gantt', title: 'Agents' })`) on the first `agent.spawn` of the session, and registers `/agent-gantt` to open it by hand.
- A `ui.render` hook on `{ component: 'Pane', requestId: 'agent-gantt' }` draws one line per row: name, indented by depth, repo, start time (`HH:MM`), end time or `running`, tokens (`12.3k`, `1.2M`), cost (`$0.42`), child count, then a bar.
- The time axis runs from `main`'s start to `now`. Each bar starts and ends at its agent's times on that axis, scaled to the pane's width.
- Under the rows: the session total from `$.session.usage()`.
- Redraws: every record change redraws the pane through `update($, atom, fn)`. While any agent runs, a 5 second `$.clock` tick moves `now` so running bars grow; the tick stops when nothing runs.

### Tests

- `mods/agent-gantt/hooks/rows.test.ts`: one table-driven test of `buildRows` covering nesting (grandchild under child under main, an orphan under main), an agent still running (`end` null) next to a finished one, and cost from a token count against a fixed price table, including an unknown model family (`cost` null).
- CI: a new job, `mod-tests`, sets up Node 24 and runs `node --test mods/agent-gantt/hooks/rows.test.ts`. Node 24 strips TypeScript types itself, so `rows.ts` uses only erasable syntax (no enums, no namespaces). The job is not added to `Required CI checks` in `project.md`.
- `test_agent_usage.py`: one case that `PRICES` loaded from `prices.json` prices a known usage to the same dollars as today. That guards the move.
- The pane drawing and the hooks get no automated test. They are checked by hand in a session (see Proof).

### Proof

The PR's Proof section shows the pane in a real session: a screenshot with the main row, two subagents (one running, one finished with its end time, tokens and cost), and a child count that matches `$.agent.list()`.

## Out of scope

- Clicking a row (separate ticket).
- Anything from before the mod loaded in this session (the history ticket).
- Shipping the mod into apps through `install.sh`.
- Pricing Codex or other providers' agents.

## Calls I made

- ⚠️ **Where the mod lives and how it ships (the ticket's Open section).** `mods/agent-gantt/` at the repo root, published through a root `.claude-plugin/marketplace.json`, installed once per machine with `/plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom`. `install.sh` stays as it is. I picked this because the pane is per person, not per app, and a user-scope install covers every repo and worktree they open. The other ways I weighed: ship it under `agent-team/` and have `install.sh` copy it into each app, then have each person point `CLAUDE_CODE_PLUGIN_DIRS` at it (two steps per app and per machine, and it changes the install copy rules); or a separate repo for the mod (one more repo to keep, and the price table lives here).
- ⚠️ **Prices move to `agent-team/scripts/prices.json`.** The ticket says reuse, not copy, and the mod can't import Python. `agent_usage.py` loads the JSON into the same `PRICES` shape, so its output doesn't change. The mod reads the file from the session's working directory, so outside a repo with the agent team the pane shows tokens without dollars.
- ⚠️ **A new CI job, `mod-tests`, on Node 24**, not added to the required checks. Adding it to `Required CI checks` would change `project.md`, which is on the approval path; that can be its own small ticket.
- Cache writes are priced at the 5m rate, because `turn.complete` gives no 1h/5m split. Agents on 1h caching will read a little low next to `agent_usage.py`.
- The main loop gets its own top row, and every subagent nests under it.
- The pane opens on the session's first subagent spawn, not at session start, so a session with no subagents never shows it. `/agent-gantt` opens it by hand.
- `repo` comes from the agent's working directory, with T3 and `.worktrees/` paths mapped to the main checkout's name.
- Running bars grow on a 5 second tick that stops when nothing runs.
- The mod's version is bumped by hand in the PR that changes it; tagged releases don't cover it.
