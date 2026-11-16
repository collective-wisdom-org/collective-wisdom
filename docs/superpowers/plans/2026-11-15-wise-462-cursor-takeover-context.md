# WISE-462 plan: read the take-over context size on Cursor

Spec: [../specs/2026-11-15-wise-462-cursor-takeover-context-design.md](../specs/2026-11-15-wise-462-cursor-takeover-context-design.md)

Test command: `python3 -I -m pytest -q agent-team/scripts`

## Task 1: `agent_usage.py`

- Add `turn=None` to `cursor_context(projects, agent, turn=None)`. With a turn, read that run's usage (same store lookup, same floor: `inputTokens` // requests); return `None` when the run has no usage yet or no such run exists in the store that has the agent. `started` stays the agent's earliest run. No turn: unchanged.
- Add `cursor_latest_turn(projects, agent)`: highest `turn_number` of the agent's runs, including runs without usage; `None` when the agent has no runs; same `LookupError` rules as `cursor_context`. Share the store lookup with `cursor_context` rather than copying it.

## Task 2: `cos_rotation_check.py`

- `read_context` keeps its `(tokens, started)` shape.
- `--record-takeover` on Cursor (`cursor=True`): when the size is `None` and `state["chiefThreadId"]` is set, ask `cursor_latest_turn` for the newest turn N and save `takeoverContext = {"threadId": chiefThreadId, "tokens": None, "turn": N}`. The line ends `; take-over context pending (turn N)`. When no run exists, behave as today. A size that reads is recorded as today.
- Plain mode on Cursor (not `--hook`): if `takeoverContext` names `chiefThreadId`, has `tokens` None and an int `turn`, call `cursor_context(projects, sid, turn)`. With a size, save `takeoverContext = {"threadId", "tokens": size}` (no `turn`) and append `; take-over context=<K>k (turn N)`. With none, change nothing and append nothing. A failed save appends `; takeoverContext not saved`. A `LookupError` here appends nothing (the main size read already decides unreadable).
- `decide` already ignores a `takeoverContext` whose `tokens` is not an int; keep that.
- Update the module docstring (pending, fill, hook stays read-only).

## Task 3: one table-driven test

In `test_cos_rotation_check.py`, one parametrized test over a fake Cursor store (use `context_store` from `test_agent_usage.py` style, as `test_plain_on_cursor_…` does): 
1. record-takeover, take-over turn running with no usage → pending saved with turn, line suffix;
2. plain check, run still running → state and line unchanged;
3. plain check after the run has usage → tokens saved, `turn` dropped, suffix `take-over context=<K>k (turn N)`;
4. record-takeover when a run already has usage → recorded at once, no `turn`.

Plus two rows in `test_cursor_context` (or one small test) for `turn=` and `cursor_latest_turn`. Keep test lines at or below the feature lines.

## Task 4: docs

- `agent-team/.claude/skills/chief-of-staff/rotation.md` take-over step 4: on Cursor the line may end `take-over context pending (turn N)`; the report then says `Take-over context pending.`; on the next working turn whose check line ends `take-over context=<K>k (turn N)`, add `Take-over context <K>k.` to that turn's report, and the 220k `Reset did not shrink the context` Cleanup check applies to that figure.
- `agent-team/.claude/skills/chief-of-staff/state-keys.md`: `takeoverContext` may be `{"threadId", "tokens": null, "turn": N}` while pending on Cursor.
- `docs/compatibility.md`: G30 (row on line 36/37 and the G30 entry near line 272) says how the size is now read on Cursor and stays open until a live reset confirms it.
- Keep agent text short; no em dashes.
