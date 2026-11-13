# CW-288 plan: attach a Cursor ticket helper's session to its ticket

Spec: `docs/superpowers/specs/2026-11-13-cw-288-cursor-helper-ticket-design.md` (approved). Follow its Design, Tests and Calls I made. It builds on CW-286, which is on `main`.

Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: `agent_usage.py --cursor-agent` prints `results`

- Read the `result` column of the agent's runs in a separate query, only in this mode. A store with no `result` column gives `[]`. `read_store` is unchanged.
- Test: `test_agent_usage.py`, extend the `test_cursor_agent` table.

## Task 2: state and snapshot in `mods/agent-gantt/hooks/cursor.ts`

- `CursorState` gains `ticket` and `request`. The first `TICKET HELPER` prompt sets `request`. New pure `withFiledTicket(state, results)`. `cursorSnapshot` passes both to `buildSnapshot`.
- Test: `cursor.test.ts`, one table.

## Task 3: hook `agent-team/scripts/cursor_gantt_hook.ts`

- `readRuns` also returns `results`. After the advance step apply `withFiledTicket`. The results text is not saved.
- Test: one row in `cursor_hook.test.ts` if cheap.

## Task 4: docs

- `docs/compatibility.md` G9, and any "not attached" wording in `README.md` or the code comments.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest` / python 3.12)
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`
- `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`
