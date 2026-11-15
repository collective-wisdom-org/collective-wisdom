# CW-341 plan: Cursor context size in the rotation check

Spec: `docs/superpowers/specs/2026-11-14-cw-341-cursor-context-size-design.md`. Test command: `python3 -I -m pytest -q agent-team/scripts` (uvx pytest if pytest is missing).

## Task 1: `cursor_context` (`agent-team/scripts/agent_usage.py`)

- Add `cursor_context(projects, agent)` after `cursor_agent_runs()`, per spec Design 1. Reuse `read_store()` for the agents and runs; open the same index.db read-only for `run_events` (`select payload_json from run_events where run_id = ?`, or a json_extract filter on `$.message.type = 'tool_call'`). Agent id as stored is `agent-<uuid>`.
- Request count = 1 + the number of distinct prefixes in `tool_call` `message.call_id`: the part before the first newline with a trailing `-<digits>` removed. Size = `inputTokens // requests` of the highest `turn_number` that has `usage_json`. `started` = earliest `coalesce(started_at, created_at)` among the agent's runs, UTC `datetime`.
- Return `None` when the agent's store has no run with usage. Raise `LookupError` when no readable store has the agent (or a store that could hold it is unreadable), when `run_events` is missing (`sqlite3.OperationalError`), or when the latest usage JSON cannot be parsed.

## Task 2: rotation check (`agent-team/scripts/cos_rotation_check.py`)

- `read_context(sid=None, cursor=False)`: with `cursor`, call `cursor_context()` with `COS_CURSOR_PROJECTS_DIR` (default `~/.cursor/projects`) and the id with `agent-` added when missing. `LookupError` raises `Unreadable("context")`. Return `(tokens, started)`, or `(None, None)` when the function returns `None`.
- `check(..., sized=True)` becomes `check(..., cursor=False)`: context is `read_context(sid, cursor)[0]` always. Plain mode passes `cursor=bool(cursor_id)`; `run_hook` passes `cursor=cursor`. `--record-takeover` saves a non-None Cursor size as before.
- Update the docstring (the "size trigger is off" paragraphs and the Cursor stop payload sentence): the size is read from the run store as a floor. Leave `decide()`, `RESET_MODES` and the line texts as they are ("ok (size unknown on Cursor)" stays for no usage yet).

## Task 3: tests, table-driven and short

- `test_agent_usage.py`: one parametrized test over a fixture `index.db` built in `tmp_path` (schema `agents`, `runs`, `run_events` as in the spec): no tool calls (size = inputTokens), two requests with parallel calls (sum // 2), latest turn wins, running or cancelled latest turn skipped, no usage yet (None), unreadable store file and store without `run_events` (LookupError), agent not in any store (LookupError).
- `test_cos_rotation_check.py`: change `test_plain_on_cursor_saves_the_conversation_id_with_the_size_trigger_off` to the new behaviour (a fixture store under `COS_CURSOR_PROJECTS_DIR`, no more `read_context` patch to raise): size line `ok (no reset on cursor; context=<N>k)` given `chiefProvider` cursor, no-usage line stays, unreadable store gives exit 2 `rotation-check: cannot read context`. Add one `--hook` Cursor case where the size is over the cap and `RESET_MODES` is patched to `{"cursor": "reset"}`: answer holds `rotate: size`. Existing tests that patched `sized=False` paths adapt.

## Task 4: docs

- `docs/compatibility.md` G8: replace the sentence "`--context` still reads Claude Code only, so a Cursor Chief of Staff has no context size." and the "no size trigger" tail with what now works (spec Design 5): the rotation check reads a Cursor size from the run store as the average prompt over the latest turn's requests, a floor; reset mode stays `none`. Keep the trial line at 174 as is. Check `agent-team/docs/agents/chief-of-staff/` and the chief-of-staff skill (`rotation.md`, `state-keys.md`) for any sentence that says Cursor has no size and fix it.
