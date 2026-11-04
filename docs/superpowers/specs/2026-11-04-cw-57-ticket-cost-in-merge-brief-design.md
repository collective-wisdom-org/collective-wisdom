# CW-57: Put the cost of each ticket in the merge brief

**Ticket:** [CW-57](https://github.com/dbeallor/collective-wisdom/issues/57)
**Status:** Shipped
**Shipped:** in PR #81, with differences: [as-built](../as-built/2026-11-04-cw-57-ticket-cost-in-merge-brief.md)

## Goals

- `scripts/agent_usage.py --ticket <PREFIX>-N` prints one line with what that ticket's child threads cost: dollars, tokens, the spec, build and merge split, how many child sessions ran, and the wall time.
- `scripts/cos_brief.py pr <N>` prints that line, so the merge block gets a `Cost:` line after `Reviews:` with no extra step for the Chief of Staff.
- The `MERGED #N` line under `Done since last report` repeats the cost, now including the merge stage.
- A `status` answer shows the cost so far in the detail cell of each active or awaiting ticket.

## Non-goals

- Budgets, alerts or any gate based on cost.
- Chief of Staff, project manager and ticket helper cost. They run in the root checkout and serve many tickets at once, so none of it is charged to a ticket.
- Children that ran on another provider (Codex). They leave no Claude Code transcript; their cost shows as `cost unknown` or leaves part of the run uncounted.
- Writing cost into release notes, as-built files, the ticket or the PR.
- Changing the existing `agent_usage.py` report (no flags given, `--turns`, `--context`).

## Design

### Which transcripts belong to a ticket

A ticket's work happens in child threads in worktrees, on the branch `feat/<prefix>-N-<short-title>` (the ship-loop pattern; `<prefix>` is the ticket prefix in lower case). `--ticket CW-57` reads the worktree project dirs the script already reads (`*<PROJECT>*` with `worktrees` in the name; root checkout dirs are skipped) and takes every session in which any line has a `gitBranch` of `feat/cw-57-…` or exactly `feat/cw-57`. The match is on the whole number, so `CW-57` never picks up `feat/cw-570-…`.

The whole session counts, including requests made before the child switched off T3's `t3/<id>` branch, since that is the start of the spec stage. Its subagent transcripts (`<session>/subagents/agent-*.jsonl`) count too.

To stay fast as the transcript dirs grow, a session file is opened for JSON parsing only if its raw text contains `"gitBranch":"feat/cw-57`. Today a full scan of every session takes about a second, so this is a margin, not a need.

`--ticket` ignores `--since` and `--until`: a ticket's cost is all of it. The argument must match `^[A-Za-z]+-[0-9]+$`; anything else exits 2.

### The split

Each request, the child's own and its subagents', goes into spec, build or merge by the stage its session was in at that moment, using the same `CHIEF OF STAFF:` relays `stage_at` already reads (`the user approved the spec` starts build, `the user approved the merge` starts merge, `Continue the <stage> stage` sets that stage).

A continuation child (a new session started with `TEAM MODE. CONTINUE`) starts in the stage its task names (`Do the <stage> stage`), not in spec. `stage_at` gets that starting stage as an argument; the existing report keeps passing `spec`, so its output doesn't change.

### The line

```
cost $14.20 API-equivalent, 38.6M tokens, spec $2.10 / build $11.66 / merge $0.44, 2 child runs, wall 5h 03m
```

- **Dollars** are API-equivalent list prices from `PRICES`, as in the existing report.
- **Tokens** are every billed token: input, output, cache reads and cache writes. Cache reads are most of it.
- **Child runs** is the number of matched sessions: one per child thread, so a continuation child or a rotation adds one. Follow-up turns in the same thread (`changes N`, a restart sent to the same child) don't.
- **Wall time** runs from the first to the last timestamped event across the matched sessions and their subagents. It includes time spent waiting on the user's approvals.

Exit codes: 0 with the line; 2 with `agent_usage: no transcripts for <ID>` on stderr when nothing matches or the projects dir can't be read.

### `cos_brief.py pr`

`cos_brief.py pr <N>` adds `headRefName` to its one `gh pr view` call. If the branch matches `feat/<prefix>-N-…`, it runs `agent_usage.py --ticket <PREFIX>-N` (by its absolute path next to `cos_brief.py`, 30 second timeout) and prints `cost: <the line>` after the review lines. Exit 2, a timeout, or a branch that doesn't match prints `cost: unknown`. A cost failure never makes `cos_brief.py` exit 2: the merge block still gets built.

### The Chief of Staff skill

- `approvals.md` § Approval requests: step 1 names the `cost:` line, and the merge block gains `Cost: <the cost line, or "unknown">` after `Reviews:`.
- `SKILL.md` § Report format: the `Done since last report` example becomes `- <PREFIX>-190 merged (#178), cost $14.20 (spec $2.10 / build $11.66 / merge $0.44)`, with one rule line: on `MERGED #N`, run `python3 scripts/agent_usage.py --ticket <PREFIX>-N` for the line; on exit 2, write `cost unknown`. This is a fresh run, not the merge-block number, because the merge stage has run since.
- `status.md` § Status layout: the detail cell ends with `$X so far` for tickets in `build`, `merge`, `awaiting-spec`, `awaiting-merge` and their queues, from one `agent_usage.py --ticket` per ticket. Exit 2 adds nothing. Tickets in `spec`, `spec-queued` and `blocked` get it too; the rule is one call per row.

PR #79 (CW-53) also edits `SKILL.md`. This change touches only the `Done since last report` lines of § Report format there, so the two merge cleanly in either order.

## Testing

- `test_agent_usage.py`: one table-driven test for `--ticket` on a fixture transcript dir. Rows: a session that starts on `t3/…` and switches to the branch, with a spec approval relay and a subagent (split and totals), a continuation session that starts in build, a `feat/cw-570-…` session and a root checkout session (both excluded), and an ID with no sessions (exit 2).
- `test_cos_brief_*.py`: one test that `cmd_pr` prints `cost: <line>` when the script succeeds and `cost: unknown` when it exits 2 or the branch doesn't match, with the script call stubbed.
- The acceptance check by hand: run `cos_brief.py pr <this PR>` and `agent_usage.py --ticket CW-57` and compare.

## Calls I made

- **Merge brief cost leaves out the merge stage.** The brief is built before the merge runs, so its merge figure is $0 or near it. The `MERGED #N` line is the full figure.
- **Root checkout work is not charged to tickets.** The Chief of Staff and project manager cost stays in the existing report only.
- **"Child runs" means child sessions**, not turns. Restarts and `changes N` sent to the same thread don't add one; a continuation child does.
- **Tokens count cache reads.** That makes the number large (tens of millions) but it is what the dollars are made of.
- **Wall time includes approval waits.** It is first to last event, as the ticket says, so a ticket that waited a day on the user shows a day.
- **Status shows cost for every row**, not only build and merge, since a call takes about a second.
- **A continuation child starts in the stage its task names** for `--ticket`. The existing report has the same gap (it puts a continuation's build in spec); it is left as it is to keep its output unchanged, and can follow in its own ticket.
- **The ticket is found by branch name**, not by the PR title or thread title, since the branch is the one thing every transcript line carries.
