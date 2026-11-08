# CW-220 plan: prices.json vs Claude Code's session cost

Spec: `docs/superpowers/specs/2026-11-08-cw-220-prices-vs-claude-session-design.md` (approved). Scratch work stays outside the repo.

## Task 1: measure before (scratch only)

Pick two finished sessions with a stored snapshot `total` (`.agent-team/gantt/*.json` in the root checkout; one Opus-led, one Sonnet-led, one with subagents). For each, compute by hand from the transcripts (dedupe by `requestId`, subagents included, writes split 5m/1h, published rates from the spec), `agent_usage.py` `costs`, the snapshot row sum and the snapshot `total`. Keep the numbers for the as-built.

## Task 2: rates and mod write split

- `agent-team/scripts/prices.json`: `sonnet.read` 0.20 to 0.10.
- `mods/agent-gantt/types/index.d.ts`: `Tokens` becomes `{ input, output, read, write_5m, write_1h }`.
- `register.tsx` `addUsage`: a turn's `cache_creation_input_tokens` goes to `write_1h` on `main` and `write_5m` for any other agent (pass the agent id in). `ZERO` follows.
- `rows.ts`: `total`, `modelCost` (export it) and `minusUsage` use the two fields; a stored record with only `write` reads as `write_1h`.
- Bump the `records` atom shape to `records-3`; keep reading old values.
- `snapshot.ts` `buildSnapshot` writes `pricing: 2`; `agent-team/scripts/dashboard/api.ts` carries `pricing` onto `Snapshot` and `Session` (number or null); `page/app.js` `renderGantt` adds one note line under the existing one when any drawn session lacks `pricing: 2`: "Some rows were priced before the CW-220 rate fix and keep their old costs."
- Bump the agent-gantt `plugin.json` version.

## Task 3: tests (budget: test lines <= feature lines)

- `agent-team/scripts/test_prices.py`: published-rate fixture (source URL, date read 2026-11-08, four models) priced against `prices.json` for one fixed usage; fails when any one rate changes. Also checks `agent_usage.costs` against the shared parity fixture.
- Shared parity fixture (JSON, next to the Python test, read by both suites): cases of model, tokens by kind with the 5m/1h split, expected dollars.
- `mods/agent-gantt/hooks/rows.test.ts`: `modelCost` against the same fixture; one table for the write split (main 1h, subagent 5m, old `write`-only record as 1h).
- A small case in the dashboard `app.test.js` / `api` test for the note and `pricing`, only if the existing tests make that cheap.

## Task 4: measure after, as-built

Re-run Task 1's numbers. Write `docs/superpowers/as-built/2026-11-08-cw-220-prices-vs-claude-session-as-built.md` with one table per session (hand, `agent_usage.py`, card, Claude Code), each remaining difference with its cause, the rate source, the Haiku over-100K dollar size, the older-version gap, and the stored-history decision. Small token-count differences between `agent_usage.py` and the mod are fixed here; larger ones are named and left for a follow-up ticket.

## Verify

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
