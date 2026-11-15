# CW-348: Keep dashboard ticket titles current when the issue title changes

**Status:** Draft
**Ticket:** [#348](https://github.com/collective-wisdom-org/collective-wisdom/issues/348)

## Goal

An open ticket row on the dashboard shows the issue's current title. When someone rewrites the issue title, the row picks it up within about a minute, without restarting the dashboard or the ticket.

## Today

Facts from main at `81c114b`.

- `cos_state.py` `start` saves `title` in `.agent-team/state.json` once, when the ticket starts. Nothing changes it after that.
- `buildApi` in `agent-team/scripts/dashboard/api.ts` builds each open row with `title: r.title || titles[r.id] || ''`, so a non-empty state title always wins.
- `server.ts` passes only the tickets with a blank state title to `trackerTitles.want(...)`.
- `createTitles` in `titles.ts` reads each title once with `gh issue view <n> --json title`, one at a time, in the background, and keeps it for good (`titles.has(id)` skips it). A failed or empty read retries after 5 minutes.
- Backlog and Todo rows already come from a fresh `gh issue list` once a minute (`backlog.ts`), and merged rows take the PR title. Only open ticket rows go stale.
- `titleCfg` is set only when the tracker is GitHub issues, so on Linear and Jira `createTitles` reads nothing.

## Design

Three small changes, all in `agent-team/scripts/dashboard/`.

### 1. `titles.ts`: titles go stale after a minute

`createTitles` keeps the time of each good read next to the title. `want(ids, cfg)` queues an id again when its last good read is 60 seconds old or more (`REFRESH_MS = 60_000`, the same cadence as `backlog.ts` and `updated.ts`).

- A good read replaces the title and its time.
- A failed or empty read keeps the last good title (it is still the newest the dashboard knows) and sets the failure time. The id is not queued again until 5 minutes after the failure (`RETRY_MS`, as today), even when its title is past `REFRESH_MS`. That stops a broken `gh` from being called every minute per ticket.
- Prefix guard, cleaning (control characters to spaces, trim, 200 characters), the one-at-a-time queue and the dedupe of queued ids stay as they are.

### 2. `server.ts`: ask for every open ticket

`trackerTitles.want(...)` gets every ticket id in `state.json`, not only the ones with a blank title. The `blank` filter goes.

### 3. `api.ts`: the tracker title wins

The open row's title becomes `titles[r.id] || r.title || ''`. The state title is the fallback while the first read is pending, when every read so far failed, and on Linear and Jira repos where `titles` stays empty.

### Cost

One `gh issue view` per open ticket per minute while the page is open. With the usual 3 to 6 open tickets that is at most a few hundred calls an hour, well inside GitHub's 5,000 an hour, and it runs only while the dashboard is polled.

## Tests

In `titles.test.ts`, the existing table test is extended rather than a new file added:

- A title read once is read again only after 60 seconds, and the second read's new title replaces the old one (acceptance: changed title shows on the second refresh).
- A failed re-read keeps the last good title and is not retried until 5 minutes later.

In `api.test.ts`, one table-driven case for the row title:

- state title and tracker title differ: the tracker title shows (acceptance 1).
- tracker title missing (failed or never read): the state title shows (acceptance 2).

## Docs

- `agent-team/.claude/skills/chief-of-staff/state-keys.md` says the `start` title is saved "so the dashboard can show it beside the ID". Reword to say the dashboard shows the tracker's current title and falls back to this one.

## Leaves out

- Merged row titles (from the PR title).
- Writing a changed title back into `state.json`.
- Linear and Jira: no tracker read from the dashboard there, so they keep the state title.
- Batching the reads into one `gh issue list` call. The per-issue read already exists and the call count is small.

## Calls I made

- **Refresh every 60 seconds**, matching the Backlog and updated-time readers. The ticket says only "without restarting".
- **A failed re-read keeps the last tracker title**, not the state title. The tracker title is newer, and dropping back to an older state title for 5 minutes would make the row flicker between the two.
- **One `gh issue view` per ticket per minute** rather than folding titles into the existing `updated.ts` list call. That list is capped at the 100 most recently updated issues, so an open ticket could fall out of it; the per-ticket read always covers every open row.
- **Failures still wait 5 minutes** before a retry, even for a title that is due for refresh.
