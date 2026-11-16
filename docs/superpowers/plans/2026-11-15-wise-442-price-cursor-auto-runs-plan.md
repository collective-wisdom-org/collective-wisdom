# WISE-442 plan: price Cursor Auto runs at a ceiling rate

Spec: [design](../specs/2026-11-15-wise-442-price-cursor-auto-runs-design.md) (approved).

## Tasks

1. **Price row.** Add the `default` row to `agent-team/scripts/prices.json` (input 10, output 50, read 0.50, write_1h 20, write_5m 12.50). Add a `test_prices.py` test that it is at or above every other row for every kind.
2. **Flag the estimate.** In `agent_usage.py` `ticket_line`, add ` (Auto at the ceiling rate)` after `, Cursor $Y` when any Cursor run is on `default`. The line still starts with `cost $`. Update the module docstring. Test with a Cursor store fixture of WISE-441 token counts (no prompt text) on `default`: a `cost $` line with the note; one run on an unpriced model: `cost unknown`. Extend the existing Cursor ticket test table if there is one.
3. **Routing test.** `test_cursor_routing.py`: drop the `UNPRICED` exception so every routed Cursor model, `default` included, must be priced.
4. **Other readers.** One case in `mods/agent-gantt/hooks/rows.test.ts` that `modelCost('default', ...)` is a number from the real `prices.json`. Add a `test_no_hands.py` row only if no case covers `ticket_cost` on a `cost $X, Cursor $Y (...)` line.
5. **Docs.** `docs/compatibility.md` (Usage and cost report Cursor cell, No Hands note, G8, G9), `chief-of-staff/models.md` line 47, and `no_hands.py` docstring mentions of Auto if any.

## Verify

`python3 -I -m pytest -q agent-team/scripts`; `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`; shellcheck per project.md.
