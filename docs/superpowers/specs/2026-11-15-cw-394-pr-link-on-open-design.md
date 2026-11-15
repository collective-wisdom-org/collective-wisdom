# CW-394: Show the PR link on the dashboard card as soon as the PR is opened

**Status:** Shipped
**Shipped:** in PR #409, as specified
**Ticket:** [#394](https://github.com/collective-wisdom-org/collective-wisdom/issues/394)

## Goal

A dashboard card shows its `PR` link from the poll after the build child opens the PR, not only once the ticket reaches MERGE READY.

## Today

Facts from main at `6f6bfe2`, `agent-team/scripts/dashboard/`.

- `buildApi` in `api.ts` sets a row's `prUrl` to `<repo.url>/pull/<pr>` only when the ticket's state `pr` is an integer. `ticket()` in `page/app.js` draws it with `prSpan(r.prUrl)`, which already skips a missing or non-http(s) url.
- State gets `pr` only from the `MERGE READY` stage op. In `build` it is `null`, so a ticket with an open PR shows `Spec` but no `PR`.
- `merged.ts` already reads merged PRs in the background with `gh pr list` (once a minute, last good list kept on failure) and maps a PR to a ticket by its head branch, `<head><prefix>-N-`, using `headsPattern` from `titles.ts`.

## Design

Look the PR up on the dashboard side. The child and the Chief of Staff don't change.

### Open PR reads (`open.ts`, new)

Same shape as `merged.ts`:

1. `parseOpen(json, cfg)` turns `gh pr list --json number,headRefName` output into `Record<ticketId, number>`. The ticket id comes from the head branch with the same `<head><prefix>-N-` pattern as `parseMerged`. A PR whose branch matches no ticket, or whose number isn't a positive integer, is skipped. Two open PRs for one ticket: the higher number wins. Bad JSON or a non-array gives null.
2. `createOpenPrs({ run, now })` runs `gh pr list --repo <slug> --state open --limit 100 --json number,headRefName` at most once a minute, in the background, one read at a time. A failed read or a null parse keeps the last good map. `want(cfg | null)`, `get()`, `idle()` match `createMerged`.

### Server (`server.ts`)

Create one `createOpenPrs` beside `createMerged` with the same `ghRunner(root)`. In `api()`, call `openPrs.want(mergedCfg)` and pass `openPrs: openPrs.get()` to `buildApi`.

### Card link (`api.ts`)

`buildApi` takes an optional `openPrs: Record<string, number>`. For each status row:

- state `pr` is an integer: `prUrl` as today (state wins).
- else `openPrs[id]` is a positive integer: `prUrl = <repo.url>/pull/<n>`.
- else no `prUrl`.

Both paths build the url the same way from `repo.url`, so the link is the same url before and after MERGE READY. The http(s) check stays in `prSpan`. A card's Details panel, CI chart, merged filter and every other use of state `pr` are unchanged.

## Test

- `open.test.ts`: one table-driven test of `parseOpen` (matching branch, other head, wrong prefix, no ticket id, bad number, two PRs for one ticket, bad JSON). One test of `createOpenPrs`: a failed read keeps the last map, and a second `want` inside a minute doesn't read again.
- `api.test.ts`: one table-driven test of a `build` row's `prUrl`: no PR anywhere (no link), an open PR (link), state `pr` plus an open PR with the same number (same url), state `pr` with no open PR (link from state).

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/open.ts` | New: `parseOpen`, `createOpenPrs`. |
| `agent-team/scripts/dashboard/open.test.ts` | New tests above. |
| `agent-team/scripts/dashboard/api.ts` | `openPrs` input; `prUrl` fallback. |
| `agent-team/scripts/dashboard/api.test.ts` | The build-row test. |
| `agent-team/scripts/dashboard/server.ts` | Create, want and pass `openPrs`. |

## Non-goals

- The card layout, the `Spec` link and the Details panel.
- When the Chief of Staff routes MERGE READY or sets `pr` and `headSha`.
- The CI wait chart for a build-stage PR (it still keys on state `pr`).

## Calls I made

- **Dashboard lookup, not a child report.** The dashboard reads open PRs with `gh pr list` once a minute. Having the child report the PR number would change the Chief of Staff's state ops and every child's protocol for a display fix; the lookup touches only the dashboard.
- **One extra `gh` call a minute**, on the same runner and the same one-minute rate as the merged list. A dashboard with no GitHub repo config makes no call.
- **Match by head branch pattern only**, like the merged list. A ticket on a branch that doesn't follow `<head><prefix>-N-` gets its link only at MERGE READY, as today.
- **State `pr` wins** over the lookup once it is set, so nothing changes for a ticket at MERGE READY or later.
- **Two open PRs for one ticket: the higher number shows.** One ticket is one PR, so this should not happen; the newest is the likely live one.
- **Limit 100 open PRs.** More open PRs than that drop the oldest from the lookup; those cards wait for MERGE READY as today.
- **The CI chart and the Details panel stay on state `pr`.** The ticket keeps them out of scope; they can follow in another ticket.
