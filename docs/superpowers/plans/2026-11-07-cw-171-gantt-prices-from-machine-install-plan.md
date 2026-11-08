# CW-171 plan: read the agent-gantt price table from the machine install

**Spec:** [2026-11-07-cw-171-gantt-prices-from-machine-install-design.md](../specs/2026-11-07-cw-171-gantt-prices-from-machine-install-design.md)

## Tasks

1. `mods/agent-gantt/hooks/register.tsx`: `PRICES_PATH` becomes `.collective-wisdom/scripts/prices.json`, read as `${HOME}/${PRICES_PATH}` with `$.env.get('HOME')` (a string literal). An unset or empty `HOME` throws into the existing `catch`. New note: `~/.collective-wisdom/scripts/prices.json is missing or unreadable. Run ./install.sh in the collective-wisdom clone.` Update the `loadPrices` doc comment.
2. `mods/agent-gantt/types/index.d.ts`: the two comments name `~/.collective-wisdom/scripts/prices.json`.
3. `README.md` (agent pane paragraph): costs come from `~/.collective-wisdom/scripts/prices.json`; the column works in an app and in this repo; a dash only when that file is missing. Keep the cache write sentence.
4. `agent-team/scripts/approval_policy.py` lines 42-43: comment only; the bare `scripts` entry exists because `gh` lists a link by that name as a file, and an old branch may still carry one.
5. `mods/agent-gantt/.claude-plugin/plugin.json`: `0.1.0` to `0.1.1`.
6. Verify: `node --test mods/agent-gantt/hooks/rows.test.ts`, `python3 -I -m pytest -q agent-team/scripts`, `claude plugin validate mods/agent-gantt`.

No new test (spec § Tests and proof).
