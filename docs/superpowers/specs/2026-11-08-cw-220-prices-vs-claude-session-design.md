# CW-220: Close the remaining gaps between prices.json and what Claude Code reports for a session

**Status:** Draft
**Ticket:** [#220](https://github.com/collective-wisdom-org/collective-wisdom/issues/220)
**Related:** CW-216 (gantt waterfall, its "Known gaps"), CW-171, CW-209 (spend on merged PRs).

## Goal

The dollar cost the team shows for a session matches what Claude Code reports for it. Where it can't match, the as-built names the remaining difference and its cause in dollars.

## Today

Facts from `main` at `73eefd9`, the published price list read on 2026-11-08, and the local transcripts (1,136 files under `~/.claude/projects/*collective-wisdom*`).

- `agent-team/scripts/prices.json` has one row per family (`opus`, `sonnet`, `haiku`, `fable`) with `input`, `output`, `read`, `write_1h` and `write_5m` in dollars per million tokens. `agent_usage.py` (`PRICES`, `costs`) and the agent-gantt mod (`rows.ts` `modelCost`, loaded by `register.tsx`) both read it.
- The published list is <https://platform.claude.com/docs/en/about-claude/pricing> (read 2026-11-08). For the versions the team runs:

  | Model | input | 5m write | 1h write | read | output |
  |---|---|---|---|---|---|
  | Claude Opus 5.5 | 4 | 5 | 8 | 0.20 | 20 |
  | Claude Sonnet 5.5 | 2 | 2.50 | 4 | **0.10** | 10 |
  | Claude Haiku 5.5 (prompt up to 100K) | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
  | Claude Fable 5.1 | 10 | 12.50 | 20 | 0.25 | 50 |

  `prices.json` matches this table except for the Sonnet read rate: it has 0.20, and the list has 0.10 (0.05x input, the same multiplier as Opus 5.5). That matches the CW-216 fit "near 0.10". The Opus read rate (0.20) is right. The cached copy of the price table in the `claude-api` skill still says Sonnet 5.5 reads cost $0.20, which is likely where the wrong number came from.
- Prices are set per model version, not per family: Opus 5 is $5/$25 with $0.50 reads, Fable 5 reads are $1, Haiku 4.5 is $1/$5, Sonnet 4.6 is $3/$15. Every request in the local transcripts is one of `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` or `claude-fable-5-1` (plus 10 `<synthetic>` lines with no price), so the family rows price today's sessions correctly.
- Every request in the transcripts has `speed: standard` and `inference_geo: global`, and none used web search. Fast mode, US-only routing and per-search charges don't explain any gap today.
- Cache writes by thread, summed over the transcripts: main threads wrote only 1h entries (Opus 5.9M, Sonnet 31.2M, Fable 1.0M tokens). Subagents wrote only 5m entries (Opus 19.3M, Sonnet 19.0M, Haiku 0.2M).
- `agent_usage.py` `costs` splits each request's writes with `cache_creation.ephemeral_1h_input_tokens` and `ephemeral_5m_input_tokens`, and falls back to the 5m rate when the split is missing. It dedupes requests by `requestId` (last line wins) and adds each session's `subagents/agent-*.jsonl`.
- The mod sums `TurnUsage` per agent and model into `Tokens` (`input`, `output`, `read`, `write`) and prices every write at `write_1h` (the comment on `modelCost` says the sessions checked wrote only 1h entries). This build's `TurnUsage` (`ModelUsage & { model }`) has `cache_creation_input_tokens` and no 5m/1h split. So the mod overprices every subagent write by 1.6x (8 against 5 for Opus, 4 against 2.50 for Sonnet).
- Claude Code's own figure reaches the dashboard as the snapshot `total`, read from `$.session.usage().cost.usd`. `app.js` prints "Claude Code reports $X for these sessions. Row costs use prices.json."
- Stored history: `spend.json` (the spend ledger, per session cost and tokens) and `gantt-history.json` (rows with `cost`, `tokens` and the top `model` only) keep the figures recorded when they were written. A row keeps neither the per-model token split nor the kinds, so it can't be re-priced.
- Haiku 5.5 bills a request whose prompt is over 100,000 tokens at 5x the rates. Two Haiku requests in the transcripts crossed it. Neither reader prices that tier.

## Design

### 1. Find each gap as a number

Pick two finished sessions from local snapshots that have a `total`: one Opus-led and one Sonnet-led, at least one with subagents (CW-216's own build session is a good candidate). For each, compute:

- **By hand**: dedupe the transcript and subagent transcripts by `requestId`, sum tokens by model and kind (writes split 5m/1h), price at the published table above.
- **prices.json via `agent_usage.py`**: `costs` summed over the same requests.
- **The card**: the sum of the snapshot's row costs, as the dashboard shows it.
- **Claude Code**: the snapshot `total`.

Do this before and after the fixes below. The as-built gets one table per session (each figure, and each difference with its cause, such as the Sonnet read rate, the 1h writes on subagents, a token count difference, or calls Claude Code makes that are in no transcript). A small script under the build's scratch space does the hand count. It is not shipped.

### 2. Fix the rates

- `prices.json` `sonnet.read` becomes `0.10`. No other rate changes, unless step 1 or a second read of the list finds another wrong one.
- The family rows stay. `prices.json` gains nothing, but the drift test (below) names the exact model each family row stands for (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`). An older version of a family is priced at the newer version's rates. The as-built names this as a known gap, not hit by any transcript today.
- The Haiku over-100K tier stays out. The as-built names it with its dollar size from the transcripts.

### 3. Make the mod split cache writes the way `agent_usage.py` does

The mod can't read the split from `TurnUsage`, so it uses the rule the transcripts show: a turn on `main` writes 1h entries, and a subagent turn writes 5m entries.

- `Tokens` gets `write_5m` and `write_1h` in place of `write`. `addUsage` puts a turn's `cache_creation_input_tokens` in `write_1h` on `main` and in `write_5m` for any other agent.
- `modelCost` prices `write_1h` at `write_1h` and `write_5m` at `write_5m`. `tokens` totals stay the same sum.
- A record stored by an older mod has `write` only: it reads as `write_1h`, which keeps its old cost. The records atom's `shape` moves up one, and the reader keeps reading the old shape.
- If a later engine adds the split to `TurnUsage`, the mod should use it. That is a follow-up, not this ticket.

`agent_usage.py` keeps its own split from the transcript. Both now price a main 1h write and a subagent 5m write the same way. Where a transcript ever disagrees with the rule (a main 5m write, a subagent 1h write), step 1's table shows it.

### 4. Same tokens in both

Step 1 checks that `agent_usage.py` and the mod count the same requests for one session: dedupe by request, subagents included once, nested subagents included. Any difference found is fixed in whichever side is wrong, in this ticket, if it is a small change in `agent_usage.py` or `register.tsx`. A larger one becomes a follow-up ticket and a named gap in the as-built.

### 5. Stored history

Leave stored figures as they are and say so on the page. Rows in `gantt-history.json` and entries in `spend.json` can't be re-priced, because they don't keep tokens by model and kind.

- The mod writes `"pricing": 2` into each snapshot it builds (`buildSnapshot`). The dashboard carries it through `api.ts` onto the session.
- `renderGantt` adds one line under the existing "Claude Code reports" note when any session drawn lacks `pricing: 2`: "Some rows were priced before the CW-220 rate fix and keep their old costs." Nothing else on the page changes.

### 6. Tests

Per `AGENTS.md` § Testing, one table-driven test per rule:

- **Drift test** (`agent-team/scripts/test_prices.py`): a fixture of the published rates for the four models above, with the source URL and the date read (2026-11-08) in a comment. For each family, price one fixed usage (every kind, with both write TTLs) from the fixture and from `prices.json` and compare. Changing any one rate in `prices.json` fails it.
- **Parity test**: the mod's `modelCost` and `agent_usage.py` `costs` give the same dollars for the same usage. A shared fixture file of cases (model, tokens by kind with the 5m/1h split, expected dollars) sits next to the tests. `test_prices.py` checks `costs` against it, and a case in `mods/agent-gantt/hooks/rows.test.ts` checks `modelCost` (exported for the test) against it. Both read the same file, so changing either reader's math fails one of them.
- **Write split rule**: a case in the existing `rows.test.ts` table: a main turn's writes price at 1h, a subagent turn's at 5m, and an old `write`-only record prices at 1h.

## Calls I made

- **Subagent writes are priced at 5m and main writes at 1h, by thread, not by a field.** The engine doesn't report the split per turn. Every one of 1,136 local transcripts follows this rule, but it is an inference: if Claude Code changes its cache TTLs, the mod drifts again. Step 1 shows any break, and the as-built names the rule as an assumption.
- **The family rows stay instead of moving to one row per model version.** Every request today is on the newest version of its family, so this fixes nothing today, and per-version keys would change both readers and the mod's stored price shape. An older version (Opus 5, Fable 5, Haiku 4.5) gets the newer rates. That is named as a gap.
- **Stored history is left as recorded, with one note line on the page.** It can't be re-priced: rows keep neither tokens by model nor the kinds. The note shows only when a drawn session predates the fix.
- **The Haiku over-100K tier is not priced.** Two requests in the local transcripts crossed it. The as-built gives its dollar size.
- **The published page is the source, not the `claude-api` skill's cached table**, which is stale for Sonnet 5.5 reads.
- **Step 1 runs on local snapshots and transcripts in this machine's root checkout and `~/.claude/projects`.** It only reads them. Nothing from them is committed except the totals in the as-built tables.
- **Token count fixes found in step 1 are in scope only when small** (a change in `agent_usage.py` or `register.tsx`). A larger one becomes a follow-up ticket.
- **The parity test reads one shared fixture from both test suites**, so the Python and TypeScript sides can't drift apart without a test failing.

## Leaves out

- New cost views, layout changes to the gantt or the dashboard (beyond the one note line).
- The subscription share (#135, #165).
- Re-pricing `spend.json` or `gantt-history.json`.
- Per-version price rows, the Haiku long-prompt tier, fast mode, `inference_geo` and web search charges (none in use today).
- Reading the cache write split from a future `TurnUsage`.

## Acceptance

- For each session checked, the card, `agent_usage.py` and Claude Code's figure agree to the cent, or the as-built names the remaining difference and its cause.
- Every rate in `prices.json` matches the published list for the model named in the drift test, with the source and date in the test.
- The drift test fails when one rate in `prices.json` changes.
- A test fails when the mod and `agent_usage.py` price the same usage differently.
