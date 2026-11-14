# CW-323: Show CI wait time on the agent gantt

**Status:** Shipped
**Ticket:** [#323](https://github.com/collective-wisdom-org/collective-wisdom/issues/323)
**Shipped:** in PR #326, as specified

## Goal

A ticket's gantt shows only the time an agent was working. While a child waits for CI nobody works, so that time is a gap and never shows. Add a `CI wait` line to each ticket's chart that says how long its PR waited on CI.

## Today

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` draws one row per task. The axis is the union of working spans, so gaps take no width (CW-216). The chart ends with a `Total` row: active time and cost.
- Sessions reach the page as `gantt` on open ticket rows (`StatusRow`) and merged entries (`MergedEntry`), built by `buildApi` in `agent-team/scripts/dashboard/api.ts`.
- GitHub reads run in the background through `ghRunner` (`titles.ts`), which calls `~/.collective-wisdom/scripts/gh.sh`. `createDetails` (`details.ts`) and `createMerged` (`merged.ts`) are the pattern: a read at most once a minute, a failed read keeps the last good result.
- Nothing reads PR check timing.

## Design

### 1. The wait, per PR (`agent-team/scripts/dashboard/ci.ts`, new)

One read per PR, a GraphQL query through `gh.sh api graphql`: the PR's last 50 commits, and for each, its check suites (first 5) and their check runs (first 20, every attempt: `filterBy:{checkType:ALL}`) with `name`, `startedAt`, `completedAt`. The query costs 3 rate-limit points a read (measured with `rateLimit{cost}`).

`ciWait(json, required)` turns that into a list of wait spans `[start, end | null]`:

- For each commit that has at least one check run: the start is the earliest `startedAt` of its runs. The end is the latest `completedAt` among its runs named in `required`, or `null` while one of them has not completed. When `required` is empty, every run on the commit counts as required.
- A commit with no check runs, or none named in `required`, gives no span.
- The list is sorted by start. Overlapping spans are not merged here; the page merges them.
- Bad JSON, or no PR in it, gives `null` (the reader keeps the last good list).

So a push that cancels a run gives two spans: the cancelled run's commit (start to its cancel time) and the new head (its start to its finish). Their overlap counts once.

`required` comes from the `Required CI checks` row of `docs/agents/project.md`: every backticked token in the Value cell, split on commas. A cell that starts with `none` gives no read at all (the repo has no CI). A missing row or a `TODO(` cell gives `[]`, so every run counts.

### 2. The reader (`createCi` in `ci.ts`)

Same shape as `createDetails`: `want(prs, cfg)` and `get()`.

- Wanted PRs: every ticket on the board whose state has a `pr` number that is not already in the merged list, and the merged entries on the merged page being shown that have recorded gantt history. A PR with no chart to draw it on is not read.
- An open PR is read at most once a minute, or once in 5 minutes when it has spans and all of them are closed. A merged PR is read once and kept while it is wanted, since its checks no longer change.
- Reads run one at a time. A failed read keeps the last good spans and is retried after a minute.
- An entry no longer wanted is dropped after a minute, like a detail.

`server.ts` creates it with `ghRunner(root)` and passes `ci: ci.get()` (keyed `<id>#<pr>`) to `buildApi`.

### 3. The api (`api.ts`)

`StatusRow` and `MergedEntry` gain `ci?: [number, number | null][]`, set only when the spans list is non-empty. A PR with no CI run sends nothing. Active-time totals, `segments` and costs are not touched.

### 4. The chart (`page/app.js`)

`renderGantt(sessions, now, ci)` takes the spans. When `ci` is non-empty:

- Below `Total`, a `CI wait` row: no bars (the axis is active time, and CI wait is the gaps), the merged length of the spans in the dashboard's duration format, and an empty cost cell. An open span runs to `now` and the row gets the `running` look the other running rows use.
- The row's tooltip: how many commits ran CI, and the first start and last end as clock times.
- `Total` stays active time only. CI wait is not added to it.
- The row shows only where a chart is drawn. A card or merged row with no sessions or no tasks shows no chart, so no `CI wait` row, and its PR is not read.

`drawCharts` passes `entry.ci` for ticket and merged charts. Chief of Staff and project manager charts pass nothing.

### 5. Tests

- `ci.test.ts`: one table-driven test for `ciWait` with the cases a single green run, a push that cancels a run and re-runs on the new head (two spans, overlap kept for the page to merge), a required run still in progress (open end), a PR with no checks (empty list), runs not in `required` ignored, empty `required` counting every run, and bad JSON (`null`). One test for the reader: an open PR re-read after a minute, a merged PR not re-read, a failed read keeping the last spans.
- `app.test.js`: one test that `renderGantt` with spans shows a `CI wait` row with the merged duration, and `Total` unchanged from the same chart without spans.
- `api.test.ts`: the `ci` spans reach the right ticket row and merged entry, and a PR with no spans has no `ci` key.

### 6. Docs

`README.md` § Local dashboard: one sentence that a ticket's chart ends with its PR's CI wait.

## Leaves out

- Review wait and merge-approval wait.
- The mod pane (Claude Code) and the Cursor hook. They draw their own charts and do not read GitHub.
- Bars for CI on the chart's axis.
- Adding CI wait to the Chief of Staff or project manager charts.
- PRs with more than 50 commits, 5 check suites per commit or 20 runs per suite: the read sees the latest 50 commits and the first suites and runs on each.
- Skipping the read for an open ticket that has no chart. Whether a snapshot matches the ticket is known only inside `buildApi`, so only merged entries without history and PRs already merged are skipped.
- Saving CI wait to `gantt-history.json`. It is re-read from GitHub each time the dashboard starts.

## Calls I made (surprising first)

- **Every push counts, not only the head commit.** The ticket says "first run on the head commit to the `checks` run finishing", but a PR's head moves on every fix. Counting only the last head would hide the earlier waits, so each commit that ran CI gives a span and the chart shows their merged total. The test covers the re-run after a push.
- **A total row, not bars.** The axis is active time, so CI wait has no place on it. The ticket allows either.
- **The wait starts when the first run starts, not when it was queued.** That is the ticket's wording. Queue time before a runner picks the job is left out.
- **A re-run of the same commit (GitHub's "Re-run jobs") counts from the commit's first run start to the last required run's end**, gap included. This is rare in this repo.
- **One GraphQL read per PR, through `gh.sh api graphql`**, instead of one REST call per commit. It also covers checks from any provider, not only GitHub Actions.
- **Query limits are 50 commits, 5 suites and 20 runs.** The first version (100, 20, 50) cost 21 points a read, and every open PR was read each minute. The smaller query costs 3, and a PR whose spans are all closed is read every 5 minutes.
- **Required names come from project.md's `Required CI checks` row**, the same row `wait-for-ci.sh` and `merge_pr.py` use. A cell that does not parse counts every run, so an app with an unset row still sees a wait.
- **A merged PR is read once per dashboard run.** Its checks are final.
- **CI wait is not saved to the gantt history.** It can always be read again from GitHub, and keeping it out leaves the history format alone.
- **One README sentence changes**, though the ticket names no doc.

## Touches

None of: data, money, auth, user email, migrations.
