# WISE-462: Read the take-over context size on Cursor

**Status:** Shipped
**Ticket:** [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462)
**Shipped:** in PR #473, with differences: [as-built](../as-built/2026-11-15-wise-462-cursor-takeover-context-as-built.md)

## Goal

After a fresh-context reset on Cursor, the Chief of Staff can read and report the context size of its take-over turn, so a run can check that the reset shrank the context (G30 in `docs/compatibility.md`).

## Today

Facts from main at `69e8093`, and from the WISE-441 trial store on this machine (`~/.cursor/projects/Users-david-beallor-Documents-cw-cursor-trial/sdk-agent-store/.../index.db`).

- On Cursor, `cos_rotation_check.py` reads the size with `agent_usage.cursor_context`: the latest run that has `usage_json`, its `inputTokens` divided by its model requests.
- Cursor writes a run's `usage_json` only when the run finishes. While a run is `RUNNING` it has no usage. The trial's post-reset Chief (`agent-570c0144…`) shows this: turn 1, the take-over turn, ran 23:18 to 23:28 and got its usage at 23:28:23.
- Take-over step 4 (`chief-of-staff/rotation.md`) runs `cos_rotation_check.py --record-takeover` as the last Bash call of the take-over turn. In a fresh conversation that turn is the only run, so no run has usage yet, `cursor_context` returns `None`, the line is `ok (no reset on cursor; size unknown)` and nothing is saved. That is the G30 failure.
- Run events give no figure either: `usage` events appear only where a queued user message splits a run (2 in that 10-minute turn), never per request.
- `agent_usage.py --context` reads Claude Code only (its docstring says so) and exits 2 without `CLAUDE_CODE_SESSION_ID`. That is the second error in the ticket.
- `takeoverContext` is `{"threadId", "tokens"}`. `decide` uses it only when `tokens` is an int at or above the size cap. On Cursor the reset mode is `none`, so the size trigger never fires there today.

## Design

### 1. Pending take-over size on Cursor

When `--record-takeover` runs on Cursor and the take-over turn has no usage yet, the script saves `takeoverContext` as `{"threadId": <chiefThreadId>, "tokens": null, "turn": <N>}`, where `N` is the turn number of the conversation's newest run (the one in progress). The line ends `; take-over context pending (turn N)` instead of nothing.

If the newest run already has usage (a take-over that did not start a new conversation), it records the size as today.

### 2. Fill it on the next check

Plain mode (no `--record-takeover`) on Cursor, when `takeoverContext` names `chiefThreadId`, has `tokens` null and an int `turn`, reads that turn's run. Once the run has usage, it saves `tokens` (the run's `inputTokens` divided by its requests, the same floor `cursor_context` uses) and drops `turn`, and the line ends `; take-over context=<K>k (turn N)`. While the run still has no usage, nothing changes and the line has no suffix. The `--hook` path stays read-only and never fills it.

A failed save adds `; takeoverContext not saved`, as `--record-takeover` does today.

### 3. `agent_usage.cursor_context` takes a turn

`cursor_context(projects, agent, turn=None)`: with a turn, it reads that run, returning `None` when the run has no usage yet. A small helper returns the newest turn number of an agent, used by step 1. Errors keep raising `LookupError` as today.

### 4. Docs

- `chief-of-staff/rotation.md` take-over step 4: on Cursor the line may end `take-over context pending (turn N)`; then the take-over report says `Take-over context pending.` On the next working turn whose check line ends `take-over context=<K>k`, add `Take-over context <K>k.` to that turn's report, and the 220k Cleanup check applies to that figure.
- `chief-of-staff/state-keys.md`: `takeoverContext` may hold `tokens: null` with `turn` while pending on Cursor.
- The `cos_rotation_check.py` docstring describes the pending and fill steps.
- `docs/compatibility.md`: G30 says how the size is now read on Cursor and stays open until a live reset confirms it.

## Leaves out

- `agent_usage.py --context` stays Claude Code only. On Cursor the size comes from `cos_rotation_check.py`.
- Turning on a reset mode for Cursor (`RESET_MODES` stays `none`).
- A live Cursor reset run to confirm G30. That is a later trial step.
- Reading a size from the transcript file (a character-count estimate). It measures something different from the pre-reset figure.

## Acceptance

- A table-driven test over a fake Cursor store: take-over turn running with no usage → pending saved with the turn; the next plain check with the run still running → no change; after the run gets usage → tokens saved, `turn` dropped, suffix printed; a take-over whose newest run already has usage → recorded at once as today.
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Calls I made

- The take-over size on Cursor is the take-over run's per-request average, read after the run ends, not a reading taken during the turn. Cursor gives no in-run figure, so the number arrives one turn late.
- The model fills it on its next plain check; the Stop hook stays read-only (its docstring says it never writes).
- `agent_usage.py --context` stays Claude Code only rather than learning to find the Cursor conversation.
- The 220k "reset did not shrink" Cleanup line moves to the turn that gets the figure on Cursor.
- No estimate from the transcript file.
