# CW-96 plan: live Gantt and cost pane mod

Spec: [design](../specs/2026-11-05-cw-96-agent-gantt-pane-design.md). Shared script edits go under `agent-team/`; the mod is at `mods/agent-gantt/`, outside it.

## Tasks

1. `agent-team/scripts/prices.json`: the current `PRICES` numbers keyed by family, each with `input`, `output`, `read`, `write_1h`, `write_5m`. `agent_usage.py` loads it into the same tuple shape (`PRICES`), so `costs()`, `family()` and the output don't change. Add one case to `test_agent_usage.py` that a known usage prices to the same dollars as the old table (hard-code the expected dollars).
2. `mods/agent-gantt/hooks/rows.ts`: `Row` type and pure `buildRows(records, agentList, prices, now)` per the spec (depth order, orphans under `main`, `childCount` from the agent list, `repo` from `cwd`, `cost` null for an unknown family or no prices, cache writes at the 5m rate). Erasable TypeScript syntax only (no enums, namespaces or parameter properties), so Node 24 runs it.
3. `mods/agent-gantt/hooks/rows.test.ts`: one table-driven `node:test` case: nesting with an orphan, a running agent beside a finished one, cost from a token count, an unknown model family.
4. `mods/agent-gantt/` plugin files: `.claude-plugin/plugin.json` (`agent-gantt`, `0.1.0`, `types` pointing at `./types/index.d.ts`), `hooks/hooks.json`, `types/index.d.ts` (the `$.state` contract), and `hooks/register.tsx`: `agent.spawn` and `turn.complete` hooks that record agents, the `ui.render` Pane hook, the `/agent-gantt` command, the 5 second tick that stops when nothing runs, the prices read from `scripts/prices.json` with `$.fs.read`. Run `claude plugin validate mods/agent-gantt` and fix what it reports.
5. `.claude-plugin/marketplace.json` at the root (`collective-wisdom`, one entry `agent-gantt` with source `./mods/agent-gantt`), checked with `claude plugin validate .`. README gets an "Agent pane" section with the install lines.
6. `.github/workflows/ci.yml`: a `mod-tests` job (Node 24, `node --test mods/agent-gantt/hooks/rows.test.ts`). Do not touch `Required CI checks` in `project.md`. Check `review_scope.py` so a change to `mods/**` does not count as docs-only.

## Verify

`python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`, `node --test mods/agent-gantt/hooks/rows.test.ts`, `claude plugin validate`.
