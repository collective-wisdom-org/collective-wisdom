# CW-284 plan: tokens and spend on Cursor gantt rows

Spec: `docs/superpowers/specs/2026-11-13-cw-284-cursor-gantt-spend-design.md` (approved). Follow its Design, Tests and Calls I made.

Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: `agent_usage.py --cursor-agent <id>`

- Split `cursor_costs` into `cursor_tokens(u)` (billed kinds) and pricing; move the per-store query out of `read_cursor` into a shared helper.
- Add `--cursor-agent` per spec § 1 (JSON on stdout, exit 2 cases, read-only). Update the docstring.
- Test: `test_agent_usage.py`, one table using `cursor_store`.
- Check: `uvx pytest -q agent-team/scripts/test_agent_usage.py` (or `uv run --python 3.12 python -m pytest`), and the whole `agent-team/scripts` suite.

## Task 2: mapping in `mods/agent-gantt/hooks/cursor.ts`

- `CursorState.runs: CursorRun[] | null`, `cursorSnapshot(..., prices)` per spec § 2.
- Test: `cursor.test.ts`, one table.

## Task 3: hook `agent-team/scripts/cursor_gantt_hook.ts`

- Run `python3 -I agent_usage.py --cursor-agent <key>` on `stop`, `subagentStop`, `sessionEnd` (3 s timeout, failures keep old runs); read `prices.json` from the hook's own folder, `null` on failure. Spec § 3.
- Test: `cursor_hook.test.ts`, two new cases.

## Task 4: docs

- `docs/compatibility.md` (G9, Local dashboard cell for Cursor, install note) and the `agent_usage.py` docstring. Spec § 4.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest` / python 3.12)
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`
- `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`
