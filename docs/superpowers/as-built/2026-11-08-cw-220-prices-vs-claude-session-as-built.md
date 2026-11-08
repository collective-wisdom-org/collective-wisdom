# As-built: prices.json against Claude Code's session cost

**Shipped:** in PR #222
**Ticket:** [#220](https://github.com/collective-wisdom-org/collective-wisdom/issues/220)
**Spec:** [2026-11-08-cw-220-prices-vs-claude-session-design.md](../specs/2026-11-08-cw-220-prices-vs-claude-session-design.md)

## Differs from the spec

- The spec said `modelCost` would be exported for the test. It is, and `addUsage` moved with it from `register.tsx` into `rows.ts`, because `register.tsx` imports `claude-code` and could not be tested.
- The spec said step 1 would price the card from the stored snapshots. Those rows came from an older mod that priced every write at 5m, so the card column is simulated: `buildRows` run over per-agent usage from the transcripts.
- The spec put `agent_usage.py` token-count fixes in scope when small. None were needed; the one difference found (requests that never finished) is left for a follow-up, see Known gaps.
- `history.ts` keeps a stored `pricing` across a reload (a missing value reads as null), so only entries written before the fix show the note.

## What changed

- `prices.json`: `sonnet.read` 0.20 to 0.10. No other rate changed. Rates source: <https://platform.claude.com/docs/en/about-claude/pricing>, read 2026-11-08. The `claude-api` skill's cached table still says 0.20 for Sonnet 5.5 reads and is stale.
- The mod prices a cache write on `main` at the 1h rate and a subagent's at the 5m rate (`Tokens` has `write_5m` and `write_1h`; `addUsage` moved from `register.tsx` into `rows.ts` so a test can reach it). A record stored with only `write` reads as 1h writes. The `records` atom is `records-3`.
- Snapshots carry `pricing: 2`. The dashboard shows "Some rows were priced before the CW-220 rate fix and keep their old costs." under a chart when any drawn session lacks it.
- `test_prices.py` checks `prices.json` against the published rates; the same `price_fixture.json` cases check `agent_usage.costs` and the mod's `modelCost`. This replaces the old restated-rates test in `test_agent_usage.py`.

## How the figures were taken

Four finished sessions with a stored snapshot `total` (root checkout `.agent-team/gantt/`), measured before the fixes and again after. Scratch scripts only; nothing from the machine is committed but the totals below.

- **By hand**: transcript plus `subagents/agent-*.jsonl`, deduped by `requestId` (last line wins), tokens by model and kind with writes split 5m/1h, priced at the published rates.
- **`agent_usage.py`**: `costs` summed over the same requests (per file).
- **Card**: the repo's `buildRows` run over the session's per-agent usage from the transcripts, summed the way the dashboard sums a chart (task rows plus agent rows). This is a simulation of the live mod, not its output. The stored snapshot rows could not be used: they were written by the CW-191 build, which priced every write at the 5m rate (36ac563d's stored task row is $0.87 against $1.09 here).
- **Claude Code**: the snapshot `total`. It equals the `cost-state` line Claude Code writes into each transcript (`totalCostUSD`) wherever that line exists.

The mod's token counts match `agent_usage.py` exactly for every agent in the two sessions with subagents (f11b21df: 18 subagents and main; a0cc835b: 8 and main), so no token fix was needed in either reader. Subagent folders hold flat `agent-*.jsonl` files only; no nested subagents turned up.

## Session 36ac563d: Opus-led, no subagents (17 requests)

| Figure | Before | After |
|---|---|---|
| By hand | $1.0933 | $1.0933 |
| `agent_usage.py` | $1.0933 | $1.0933 |
| Card | $1.0933 | $1.0933 |
| Claude Code | $1.0935 | $1.0935 |

Remaining difference, $0.0002: Claude Code's `cost-state` lists 1,812 Haiku input tokens ($0.00019) that are in no transcript. Nothing in this session was affected by the fixes (Opus reads were already right, all writes were 1h).

## Session 1ede99ab: Sonnet-led, no subagents (133 requests, root checkout Chief of Staff thread)

| Figure | Before | After |
|---|---|---|
| By hand | $3.6261 | $3.6261 |
| `agent_usage.py` | $5.8456 | $3.6261 |
| Card | $5.8456 | $3.6261 |
| Claude Code | $3.5812 | $3.5812 |

- Fixed: the Sonnet read rate. 22.2M read tokens at the extra $0.10/MTok were $2.22 of the gap.
- Remaining difference, $0.0449: two requests in the transcript never finished (the last line of each has no `stop_reason`; 8 and 64 output tokens, $0.0238 and $0.0212) and Claude Code's total leaves them out (its Sonnet tokens equal the transcript's minus exactly those two). $0.00013 more is Haiku calls in no transcript. Neither `agent_usage.py` nor the hand count skips unfinished requests. Whether the mod's `turn.complete` usage counts them is not known.

## Session f11b21df: Sonnet-led, 18 subagents (420 requests: main Sonnet, subagents Sonnet and Opus)

| Figure | Before | After |
|---|---|---|
| By hand | $16.3510 | $16.3510 |
| `agent_usage.py` | $20.0417 | $16.3510 |
| Card | $23.3889 | $16.3510 |
| Claude Code | $16.3512 | $16.3512 |

- Fixed, `agent_usage.py` against hand, $3.69: the Sonnet read rate (36.9M read tokens, main and subagents).
- Fixed, card against `agent_usage.py`, $3.35: subagent writes priced at 1h instead of 5m (Opus 437K tokens, $1.31; Sonnet 1.36M tokens, $2.04).
- Remaining difference, $0.0002: Haiku calls in no transcript (`cost-state` shows 2,205 Haiku input tokens).

## Session a0cc835b: Opus and Sonnet on main, 8 subagents (158 requests)

| Figure | Before | After |
|---|---|---|
| By hand | $5.7458 | $5.7458 |
| `agent_usage.py` | $6.7314 | $5.7458 |
| Card | $7.6130 | $5.7458 |
| Claude Code | $5.7460 | $5.7460 |

- Fixed: Sonnet read rate $0.99; subagent writes at 1h instead of 5m $0.88 (Opus 203K tokens, Sonnet 181K).
- Remaining difference, $0.0002: the same size as the Haiku calls in the other sessions. This transcript has no `cost-state` line, so the cause is inferred, not shown.

## Across all stored snapshots

With the published rates and the unfinished requests left out, the hand count is within half a cent of the snapshot `total` for 82 of the 85 snapshots whose transcript is here. Counting them, 78 of 85. The three that miss: da6dc5d4 (hand $0.012 under Claude Code), e86b8320 (hand $0.024 under) and dde8432e, a session still running when this was taken. The first two were not looked into.

## Known gaps left open

- **Unfinished requests.** Claude Code leaves them out of its total; `agent_usage.py` counts them ($0.19 across the 5 stored sessions that have any). A fix is small in `read_session` (skip a request whose last line has no `stop_reason`), but it also feeds `--context` and `--turns`, where the newest request of a running session may not have one. Needs its own ticket, with a look at what the mod counts.
- **Calls in no transcript.** Claude Code's total includes small Haiku calls (about $0.0002 a session) that appear in no transcript. Not reachable from either reader.
- **Haiku prompts over 100K tokens** bill at 5x. Two requests in the local transcripts (116K and 126K tokens, one subagent) crossed it; they are priced at the standard rate, $0.0113 together. At 5x the extra is $0.045. Neither reader prices the tier.
- **Older model versions** are priced at the newer version's rates (the family rows stand for Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1; Opus 5 is $5/$25 with $0.50 reads, for example). No local request used one: the 1,139 transcript files hold only `claude-sonnet-5-5` (13,905 requests), `claude-opus-5-5` (5,406), `claude-fable-5-1` (218) and `claude-haiku-5-5` (10), so the gap is $0 today.
- **The write split is an inference.** The mod uses main equals 1h and subagent equals 5m because every request in the local transcripts follows it (11,315 main requests with no 5m write, 8,264 subagent requests with no 1h write). If Claude Code changes its cache lifetimes, the card drifts again until `TurnUsage` carries the split. A transcript that breaks the rule shows up as an `agent_usage.py` against card difference in this kind of table.
- **Fast mode, US-only routing and web search** are not in use in any local request, so they explain no gap.

## Stored history

Left as recorded. `spend.json` and `gantt-history.json` keep cost and tokens per row without the model or the kinds, so they cannot be re-priced. Snapshots written before this change have no `pricing` field, and a chart that draws one shows the note line. The `records-3` shape means a mod session that was open across the upgrade starts its record afresh (the atom's old value is read as the initial); the `write`-only reader stays for any record that still arrives in the old form.
