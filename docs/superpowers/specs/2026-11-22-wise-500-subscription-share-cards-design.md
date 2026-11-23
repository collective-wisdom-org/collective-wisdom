# WISE-500: Show the share of the Claude subscription on dashboard cards

**Status:** Shipped
**Ticket:** [#500](https://github.com/collective-wisdom-org/collective-wisdom/issues/500)
**Shipped:** in PR #502, as specified

## Goal

When `~/.config/collective-wisdom/user.md` sets `Claude subscription API-equivalent usage (dollars)`, the dashboard's merged cards and open card footers show `(P% of the subscription)` after the dollar cost, with the same rule and format as `agent_usage.py --ticket`. The share counts Claude Code dollars only. With the row unset, the cards look as they do today.

## Today

- `agent_usage.py` `share(cost, usage)` builds ` (P% of the subscription)`: two decimals, `<0.01` when `0 < pct < 0.005`, `""` when usage is unset. `main()` reads usage with `user_config.subscription_usage("Claude")`: a positive finite number, else `None`.
- `user_config.py` has a CLI with `account` and `path` only. The dashboard server (`dashboard/server.ts`) never reads user.md.
- The spend ledger (`dashboard/spend.ts`) stores one `cost` per session (`session.total`), with no harness. `spendByTicket()` sums it into `{ cost, tokens }`, which `buildApi` attaches to merged entries as `e.spend`; `renderMerged` prints `dollars(e.spend.cost)`.
- An open card footer is `summaryLine()` → `ganttSummary()`, which sums the row costs of the card's Gantt sessions (null when any row is unpriced). A session is Cursor when every row has `harness: 'Cursor'` (the same test `cleanWith` in `api.ts` uses).

## Change

1. **`user_config.py subscription <provider>`**: a new CLI subcommand that prints `subscription_usage(provider)` (Python's `repr` of the float, e.g. `12000.0`) and nothing when it is `None`, exit 0. A `UserConfigError` (an unreadable user.md) prints nothing and exits 0, the same as `agent_usage.py` treating it as unset. The module docstring lists it.

2. **Server reads it** (`dashboard/server.ts`): a small cached reader runs `python3 -I <scripts>/user_config.py subscription Claude` with `execFile` (2 s timeout), the same way `cos_user_check.py` is called. Output that parses as a positive finite number is the figure; empty output, a non-zero exit, a timeout or a spawn error is `null`. It runs at start and then at most once a minute when `/api` is built, so editing user.md shows up within a minute without a restart. There is no second parser of user.md in TypeScript.

3. **`/api` field**: `Api` gets `subscription: number | null`, passed into `buildApi` and copied as is (anything but a positive finite number becomes `null`).

4. **Ledger split** (`dashboard/spend.ts`): `SpendEntry` gets `claude: number | null`, the Claude Code part of `cost`. `recordSpend` sets it to `cost` for a Claude Code session and `0` for a Cursor session (every row on `Cursor`); with `cost` null it is null. `parseLedger` keeps an entry whose `claude` is missing by reading it as `cost` (all Claude Code), and drops one whose `claude` is present but not null or a non-negative number. A session still in the snapshots is rewritten with the split on the next 30 second round, since an equal `updatedAt` replaces the entry. `Spend` (per ticket) gets `claude: number | null`, summed like `cost`.

5. **The share text** (`page/app.js`): an exported `subscriptionShare(cost, usage)` that returns ` (P% of the subscription)` with `share()`'s exact format, and `''` when `usage` is not a positive number or `cost` is not a positive number.

6. **Merged card**: the cost part becomes `dollars(e.spend.cost) + subscriptionShare(e.spend.claude, api.subscription)`, for example `$73.86 (0.62% of the subscription)`. `renderMerged` takes the figure as a new trailing argument.

7. **Open card footer**: `ganttSummary()` also returns `claude`, the sum of the row costs of the non-Cursor sessions (null when any of those rows is unpriced). `summaryLine(gantt, now, usage)` appends `subscriptionShare(g.claude, usage)` after the dollars, and only when the dollars are shown. The 1 second refresh of `.summary` spans passes the same figure, so the text stays identical between polls.

8. **Tests**, one table-driven test per rule:
   - `app.test.js`: `subscriptionShare` and the footer: usage `12000` with $73.86 gives `0.62%`; a tiny cost gives `<0.01`; usage `null`, `0`, negative, `NaN` give `''`; a Claude part of `0` (an all-Cursor ticket) gives `''`; a mixed Claude Code and Cursor gantt shows the share of the Claude Code rows only.
   - `spend.test.ts`: extend the ledger table with a Cursor session (claude 0), a mixed ticket's `claude` sum, an old entry without `claude` (reads as `cost`), and a bad `claude` dropped.
   - `test_user_config.py` (or the existing user_config test file): the `subscription` subcommand prints the figure, and prints nothing for unset, `none`, `0`, `-5`, `12,000` and text. One table over the same cases `subscription_usage` already uses.

## Leaves out

- Other providers' subscriptions and reading the real usage figure from Claude.
- Any change to `agent_usage.py` output or the user.md row.
- The Details panel's `Cost` fact and the Gantt chart's Total row: they keep plain dollars.
- The Chief of Staff and project manager tabs.

## Calls I made

- **The share sits on the card's dollar figure, which still includes Cursor dollars; only the percentage leaves them out.** A ticket with $10 Claude Code and $5 Cursor shows `$15.00 (0.08% of the subscription)` at 12000. Splitting the dollar figure would change what cards show today, which the ticket does not ask for. `agent_usage.py --ticket` does the same: total cost, share of the Claude Code part.
- **"Known to be Cursor" for old ledger entries means a session still in a snapshot.** An old entry carries no harness, so it reads as all Claude Code until its snapshot is recorded again with the split. Cursor sessions that left the snapshots before this ships stay counted as Claude Code. Guessing from the gantt history would add a second source for the same fact.
- **The server shells out to `user_config.py`** instead of parsing user.md in TypeScript, so there is one rule (the ticket's preference). Python float parsing accepts forms like `1e4`; the share follows whatever `subscription_usage` returns, so the two can never disagree.
- **The figure is cached for a minute**, not read on every `/api` call (the page polls often) and not only at start (a user.md edit should not need a restart).
- **The dashboard's dollars are the snapshot totals, not `agent_usage.py`'s transcript prices.** The share uses the same formula, so for the same dollar figure it prints the same percentage; if the two dollar figures differ, the percentages differ by the same ratio.
- **A Cursor session is one where every row is on the `Cursor` harness**, the rule `api.ts` already uses, not a per-row split. A Claude Code session never has Cursor rows today.
- **No share when the cost is unknown or zero**: an unpriced open card shows no dollars today, so it shows no share either.
