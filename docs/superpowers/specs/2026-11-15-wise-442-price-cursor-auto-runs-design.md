# WISE-442: Price Cursor Auto runs in the usage and cost report

**Status:** Draft
**Ticket:** [#442](https://github.com/collective-wisdom-org/collective-wisdom/issues/442)

## Decision needed first

The ticket says: if Cursor's run store does not name the model an Auto request was routed to, say what estimate is possible and stop for a decision before building one. It does not name it. This spec proposes one estimate, a **ceiling rate**, and approving the spec approves that estimate. The options are under [Estimates](#estimates).

## Goal

A Cursor ticket whose runs are all on Auto gets a dollar cost that is never below what the runs could have cost at any rate the team knows, so the cost report, the gantt, the dashboard spend and the No Hands cost cap stop treating every Cursor ticket as `cost unknown`.

## Today

Facts from main at `45ef2d7`.

- Every Cursor role routes to `default` (Auto), WISE-459. The ticket's `auto-smart` is the name before that.
- `agent-team/scripts/prices.json` has no `default` row. `agent_usage.family("default")` is `None`, so `cursor_costs` returns no dollars and `ticket_line` prints `cost unknown (no price for default; $X priced)`.
- The agent-gantt mod (`mods/agent-gantt/hooks/rows.ts` `modelCost`) and the Cursor gantt hook (`agent-team/scripts/cursor_gantt_hook.ts`) price from the same `prices.json`, by the same substring match on the family key. A `default` run gets `cost: null`, so the gantt shows a dash and the dashboard spend adds its tokens but not its dollars (`dashboard/spend.ts`).
- `no_hands.py` `ticket_cost` reads `cost $X` from `agent_usage.py --ticket`. `cost unknown` makes it `None`, and `evaluate` stops the run with `no-hands: stop cost unknown (<ticket>)`.
- `test_cursor_routing.py` keeps `UNPRICED = "default"` as the one routed model allowed to have no price, and asserts `family("default") is None` ("the day Auto gets a price, drop the exception").

### What the WISE-441 run store records

Read from the trial's stores under `~/.cursor/projects/*cw-cursor-trial*/sdk-agent-store/*/index.db`:

- `runs.model` is `default` on every Auto run, `model_params_json` is empty, and `usage_json` has `inputTokens`, `outputTokens`, `cacheReadTokens`, `cacheWriteTokens`, `totalTokens` and `reasoningTokens`. Nothing names a routed model.
- `run_events.payload_json` names other models (`claude-opus-5-5`, `claude-sonnet-5-5`, `composer-2.5-fast`), but only as arguments of tool calls (a `delegate_task` target, a subagent request), not as the model that served the run.
- `agents.metadata_json` holds an encryption key and the initial mode only.

So the routed model cannot be read, and the run cannot be priced exactly.

### What Cursor publishes about Auto

From `https://cursor.com/docs/models-and-pricing`, read 2026-11-15 (the Auto section came back as a summary, not verbatim text):

- Auto has no per-token rate of its own. Balance and Intelligence modes bill at the routed model's list price, plus a Cursor token rate (given as $0.25/MTok) on Teams and Enterprise for third-party models. Cost mode bills as a Cursor-model request.
- Cursor does not publish which models Auto may route to.

## Estimates

1. **Ceiling rate (proposed).** A `default` row in `prices.json` whose rate for each token kind is the highest rate of that kind in the other rows: input $10, output $50, cache read $0.50, cache write 5m $12.50, cache write 1h $20 per MTok (Fable's input, output and writes, Grok 4.7's cache read). A test keeps it at or above every other row, so adding a dearer row raises it. The number is high on purpose: on one WISE-441 run (383K input, 343K cache read, 4K output) it is about $0.78, where Composer 2.5's rate gives about $0.10. It is never low against any model the team prices; it can be low only if Auto routes to a model dearer than Fable, which nothing published says it does.
2. **A reference model's rate**, for example Composer 2.5 or Sonnet. Closer to a typical bill, but low whenever Auto routes to something dearer. The ticket rules this out ("Never show a low number").
3. **Keep `cost unknown`** and change nothing but the docs. No Hands under a Cursor Chief of Staff keeps stopping on the first Cursor ticket.

## Design

### 1. Price row

Add `"default": { "input": 10, "output": 50, "read": 0.50, "write_1h": 20, "write_5m": 12.50 }` to `agent-team/scripts/prices.json`. `agent_usage.py`, the gantt hook and the mod all pick it up with no code change, since they share the file and the family match. No Claude model id contains `default`.

### 2. Say it is an estimate

`ticket_line` adds ` (Auto at the ceiling rate)` after the `Cursor $Y` part when any of the ticket's Cursor runs is on `default`, so the line reads `cost $X API-equivalent, Cursor $Y (Auto at the ceiling rate), ...`. It still starts with `cost $`, so `no_hands.py`'s `COST` match is unchanged. The full report's Cursor rows are left as they are (its header already says prices are list prices).

### 3. Unpriced stays unpriced

A Cursor run on a model with no row (Gemini, Grok 4.6, a null model) still makes the ticket `cost unknown`. Nothing in the unpriced path changes.

### 4. Tests

- `test_prices.py`: one test that the `default` row is at or above every other row for every token kind.
- `test_agent_usage.py` (or the existing Cursor ticket tests): a store fixture built from WISE-441 run usage (token counts only, no prompt text), all on `default`, gives a `cost $` line with the ceiling note; the same fixture with one run on an unpriced model gives `cost unknown`. Reuse the existing table-driven Cursor ticket test if one exists.
- `test_cursor_routing.py`: drop the `UNPRICED` exception, so every routed Cursor model must be priced, `default` included.
- `test_no_hands.py`: only if no existing case covers `ticket_cost` reading a `cost $X ..., Cursor $Y (...)` line; one row in its table.
- Gantt: one case in `mods/agent-gantt/hooks/rows.test.ts` that `modelCost('default', ...)` is a number from the real `prices.json`.

### 5. Docs

- `docs/compatibility.md`: the Cursor cell of the Usage and cost report row, the No Hands note under Matrix 1, G8 and G9 say Auto runs are priced at the ceiling rate and that a ticket line flags it. G31's check 4 stays a record of the WISE-441 run.
- `agent_usage.py` docstring: the ceiling note in the `--ticket` format.
- `chief-of-staff/models.md` § Cursor, if it says Auto is unpriced.

## Out of scope

- Fast mode and Grok long-prompt pricing (ticket).
- Codex and Antigravity costs (ticket).
- The Cursor token rate on Teams and Enterprise: the ceiling's input and output rates already sit far above it.
- The gantt snapshots' null `ticket` and `request` that stop a Cursor helper joining its ticket's spend: [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463). This ticket makes the dollars non-null where the join already works (worktree children by branch).
- Changing the No Hands cost cap.

## Calls I made

- **Estimate the price at a ceiling rather than leave it unknown.** The ticket asks to stop for this decision; approving the spec makes it.
- The ceiling is the per-kind maximum of the existing rows, not one model's rate, so no kind is priced below a known model.
- A No Hands run under a Cursor Chief of Staff will hit its $200 cap sooner than its real spend, by roughly 5 to 8 times on the WISE-441 token mix. That is the safe direction.
- The `--ticket` line flags the estimate in words instead of a new field, so existing parsers keep working.
- The gantt and dashboard show the ceiling dollars with no estimate mark: the mod has no field for it, and adding one is more than this ticket.
- Cursor's Auto docs were read as a fetched summary; the claim "no per-token Auto rate" rests on it and on the ticket.
