# CW-257: Include Cursor sessions in the usage and cost report

**Status:** Shipped
**Shipped:** in PR #269, with differences: [as-built](../as-built/2026-11-08-cw-257-cursor-usage-report.md)
**Ticket:** [#257](https://github.com/collective-wisdom-org/collective-wisdom/issues/257)

## Goal

A ticket worked on Cursor in T3 Code shows a cost in the merge brief, the status table and the No Hands cost cap, priced from `prices.json` like Claude Code work. When Cursor ran a model `prices.json` has no price for, the report says `cost unknown` with the reason, never a figure that leaves that work out, and No Hands stops as it does today for an unknown cost.

## Today

Facts from `main` at `cbc35dc`.

- `agent_usage.py` reads only Claude Code transcripts under `~/.claude/projects` (`--projects`). `--ticket` matches worktree sessions by `gitBranch` `feat/<prefix>-N`, splits cost into spec, build and merge at the `CHIEF OF STAFF:` relays, and prints `cost $X API-equivalent[ (P% of the subscription)], N.NM tokens, spec $a / build $b / merge $c, K child runs, wall Hh MMm`, or exits 2 with `no transcripts for <ticket>`.
- `cos_brief.py` `cost_line` prints `cost: <that line>`, or `cost: unknown` on any failure. `no_hands.py` `ticket_cost` reads `cost \$X` from the start of the line; no match is an unknown cost, and an unknown cost stops the run with `no-hands: stop cost unknown`. `chief-of-staff/status.md` adds `$X so far` from the same line.
- `docs/compatibility.md` marks the cost report `not supported` for Cursor (G8).

## What Cursor records

Looked at on this machine (Cursor driven by T3 Code, `~/.cursor/projects`), two sources per project dir. Project dirs are named after the checkout path the same way Claude Code names them (`Users-david-beallor-t3-worktrees-<app>-<id>`).

1. **`sdk-agent-store/<hash>/index.db`** (SQLite, WAL). Table `agents`: one row per T3 thread (`name` is `T3 Code <thread id>`, `workspace_ref` is the checkout path). Table `runs`: one row per turn, with `agent_id`, `turn_number`, `status`, `model` (for example `claude-opus-5-5`, `grok-4.7`, `default` on a cancelled turn), `started_at`, `finished_at` and `usage_json`:
   `{"inputTokens":90449,"outputTokens":1023,"cacheReadTokens":59528,"cacheWriteTokens":30913,"totalTokens":181913,"reasoningTokens":…}`.
   `inputTokens` includes the cache reads and writes: in every sampled run `inputTokens >= cacheReadTokens + cacheWriteTokens`, and in the Opus sample above the difference is 8 tokens. `totalTokens` is the sum of all four fields, so it counts cache tokens twice. Cache writes carry no 5 minute or 1 hour split.
2. **`agent-transcripts/<agent_id>/<agent_id>.jsonl`**: `{role, message: {content}}` lines with no timestamps and no usage. User messages are in turn order, each wrapped as `<timestamp>…</timestamp>\n<user_query>\n…\n</user_query>`. A `subagents/` folder beside it holds subagent transcripts, also with no usage, and subagents have no `runs` rows of their own.

`~/.cursor/ai-tracking/ai-code-tracking.db` holds code-line attribution and conversation summaries, with no token counts. It is not used.

So Cursor records enough: model, tokens and time per turn. No branch is stored.

## Design

### 1. Read Cursor runs in `agent_usage.py`

A new `--cursor-projects DIR` flag, default `~/.cursor/projects`. A missing dir means no Cursor runs. The same project match as Claude Code applies: dirs whose name contains `PROJECT`, and `worktrees` in the name means a worktree session.

`read_cursor(proj)` opens each `sdk-agent-store/*/index.db` read-only (`file:…?mode=ro` URI, so nothing is written and the WAL is still read) and returns one session per `agents` row that has runs: its agent id, `workspace_ref`, the first user message and the relays from its transcript, and its runs. A store that fails to open or query prints one `agent_usage: cannot read <path>` line on stderr and is skipped. A run is `(time, model, family, costs, tokens, turn_number)`, with `time` the run's `started_at` (else `created_at`). A run with no `usage_json` (cancelled before any request) is skipped.

Pricing a run, per million tokens from `prices.json` by `family(model)`:

- input: `inputTokens − cacheReadTokens − cacheWriteTokens`, floored at 0, at the input rate
- output: `outputTokens` at the output rate (reasoning tokens are part of it and not added again)
- cache read: `cacheReadTokens` at the read rate
- cache write: `cacheWriteTokens` at the 5 minute write rate
- tokens: input + output + cache read + cache write as above (not `totalTokens`)

A run whose model has no family in `prices.json` is **unpriced**: its tokens count, its dollars do not, and its model name is kept.

User text is the part inside `<user_query>…</user_query>` when present, else the whole text. Relays are user messages that start with `CHIEF OF STAFF:`; the nth user message belongs to turn n, so a run's stage is `stage_at` over the relays of turns up to and including its own. The run's time doesn't enter the stage split.

### 2. Which ticket a Cursor session belongs to

Claude Code stores the branch on every line; Cursor does not. A worktree session's branch is, in order:

1. the `Branch: feat/<…>` line of its first user message (every ship-loop child task has one), else
2. `git -C <workspace_ref> branch --show-current`, when that dir still exists.

A session with neither is grouped under its agent id in the window report and never matches a ticket.

### 3. `--ticket`

`ticket_line` adds the matching Cursor worktree sessions: each is one child run, its runs add to the stage dollars and tokens, and its run times add to the wall span. The continuation start stage comes from its first user message as for Claude Code.

When every matching run is priced, the line is unchanged in shape. When the ticket has Cursor runs, the subscription share is computed on the Claude Code part only (the subscription is Claude's), and the line adds `, Cursor $Y` after the cost part:

`cost $12.40 API-equivalent (3.10% of the subscription), Cursor $4.10, 9.8M tokens, spec … , 3 child runs, wall 2h 05m`

When any matching run is unpriced, the line starts `cost unknown` instead, names the models, and keeps the priced figures:

`cost unknown (no price for grok-4.7; $8.30 priced), 9.8M tokens, spec $1.20 / build $6.00 / merge $1.10, 3 child runs, wall 2h 05m`

It still exits 0. `no transcripts for <ticket>` (exit 2) now means no Claude Code session and no Cursor session ran the ticket.

### 4. The window report

Cursor worktree sessions join the child rows (by branch, as Claude Code sessions are, so a ticket worked on both shows one row) and the `children` token split. Cursor root sessions get a row `root cursor <id8> <first message>`. Unpriced runs add one line after the totals: `not priced: <model> <N> runs, <M>M tokens` per model. `--turns` and `--context` stay Claude Code only.

### 5. Callers

- `cos_brief.py`: no code change. The brief shows `cost: cost unknown (no price for …)`, which says why.
- `no_hands.py`: `ticket_cost` already returns None when the line has no `cost $X`, so an unpriced Cursor run stops the run. The stop line names the ticket: `no-hands: stop cost unknown (<PREFIX>-N)`, the first ticket in run order whose cost is unknown.
- `chief-of-staff/status.md`: the detail cell ends with `cost unknown` when the line starts that way.
- `chief-of-staff/SKILL.md` § MERGED: the `Done since last report` cost reads `cost unknown` the same way.

## Tests

In `test_agent_usage.py`, with a fixture builder that writes an `index.db` (`agents` and `runs` tables with only the columns read) and a transcript:

- One table-driven `--ticket` test: a Claude Code session plus a priced Cursor session on the same branch gives the summed cost, the `Cursor $Y` part, the share on the Claude part only, and the run count; a Cursor run on `grok-4.7` gives `cost unknown (no price for grok-4.7; $… priced)`; a Cursor session whose branch comes only from `git branch` of its `workspace_ref` matches; a Cursor session on another branch does not; a cancelled run with no usage adds nothing. Dollar values are checked against hand-computed prices, including the cache-inclusive input.
- One stage-split case: a relay in turn 2 puts turn 1 in spec and turns 2 and 3 in build.

In `test_no_hands.py`, the existing `cost unknown` cases expect the ticket in the stop line.

`python3 -I -m pytest -q agent-team/scripts` passes.

## Docs

- `docs/compatibility.md`: the Cursor cell of "Usage and cost report" becomes `🟡 partial: models without a price show cost unknown (G8)`, the No Hands note says a Cursor child is priced and an unpriced model stops the run, and G8 says Codex and Antigravity are still not read and Cursor runs on unpriced models are unknown.
- `agent_usage.py` docstring: the Cursor source, the new flag and both new line shapes.
- `no_hands.py` docstring and `chief-of-staff/no-hands.md`: the stop line names the ticket.
- `README.md`: one line where `agent_usage.py` is described, if it says Claude Code only.

## Leaves out

- Codex and Antigravity cost (out of scope in the ticket).
- Prices for non-Anthropic models such as `grok-4.7` or Cursor's `default`/`auto`. They show as unknown; adding a price is a `prices.json` change in its own ticket.
- Cursor subagents as their own rows. They have no usage records; whether the parent run's usage includes them is not known (see Calls).
- The dashboard and `agent-gantt` spend (G9).

## Calls I made

- **Unpriced models make the whole ticket `cost unknown`**, not a lower figure. A No Hands run on a cheap non-Anthropic model therefore stops at its first cost check. The ticket asks for unknown, not zero, and a partial figure under a cost cap is the same risk as zero.
- **`inputTokens` is read as including cache tokens**, from the samples above, not from Cursor docs. If it is wrong, Cursor input is overcounted by the cache tokens at the input rate, which errs high.
- **Cache writes are priced at the 5 minute rate**, since Cursor gives no split.
- **Cursor's own price is not used.** The figure is API list price from `prices.json`, the same API-equivalent figure as Claude Code, not what Cursor bills.
- **Subagent work is assumed to be inside the parent turn's usage**, or not counted. Cursor records no usage for subagents; the report can't tell which.
- **The branch comes from the task's `Branch:` line first, then `git`.** A worktree that is archived and whose task had no `Branch:` line is not matched to its ticket.
- **The subscription share counts only Claude Code dollars**, and the Cursor part is shown on its own, so the share keeps meaning the Claude subscription.
- **The No Hands stop line names the ticket**, a small change to an exact line the tests and `no-hands.md` quote.
- **`--turns` and `--context` stay Claude Code only**: they serve the Chief of Staff thread's rotation, which runs on Claude Code.
