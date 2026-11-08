# CW-247: Add a Chief of Staff tab to the dashboard

**Status:** Draft
**Ticket:** [#247](https://github.com/collective-wisdom-org/collective-wisdom/issues/247)

## Goal

The dashboard gets two tabs. **Ship loop** is today's page, unchanged. **Chief of Staff** shows a card for the Chief of Staff with the gantt of its current session, and a list of the project manager's threads (Backlog ranking and hygiene children), each with its gantt, newest first. Finished project manager threads stay in the list.

## Today

- `cleanSnapshot` (`agent-team/scripts/dashboard/api.ts`) drops every snapshot whose cwd is not a worktree, so sessions in the root checkout (the Chief of Staff, its project manager children, its helpers) never reach the page.
- A snapshot (`buildSnapshot` in `mods/agent-gantt/hooks/snapshot.ts`) has `sessionId`, `cwd`, `updatedAt`, `total`, `pricing`, `rows`. Nothing in it says which thread or role it is.
- State already has `chiefSessionId` (saved by the rotation check on every plain Chief of Staff run) and `chiefThreadId`. It has no list of project manager threads.
- Every T3 session has `T3CODE_THREAD_ID` in its environment. For a delegated child it is the same string the Chief of Staff saves as `childThreadId` (checked on this machine: `thread:delegated-task:command%3Amcp%3A…`).
- The project manager children are started with `delegate_task`, titled `Backlog ranking` and `Project manager hygiene`. T3 puts one line before the task (`Act as the research sub-agent for this task.`), then the task, whose first line is `BACKLOG RANKING. One-shot, read only.` or `PROJECT MANAGER HYGIENE. One-shot.` (`agent-team/.claude/skills/project-manager/reference.md`).
- `gantt-history.json` (`history.ts`) keeps up to 500 sessions matched to tickets. Live snapshots older than 24 hours are dropped.

## Design

### 1. Snapshot: thread id and heading (agent-gantt mod)

`buildSnapshot` gets two new fields, both `null` when unknown:

- `threadId`: `T3CODE_THREAD_ID`, read once with the harness (`ensureHarness` already reads it). Outside T3 it is `null`.
- `heading`: taken from the session's first real prompt in `prompt.submit` (the same prompt that names the first task). Look at its first 5 lines and take the first one that matches `^[A-Z][A-Z ]{2,38}[A-Z]\.` (capital words ending in a period, like `BACKLOG RANKING.` or `TEAM MODE.`). Store the match without the period in a new atom; set it once and never change it. No match: `null`.

The mod knows nothing about team roles. It only reports the heading; the dashboard decides what it means. That keeps the team's words out of the mod, and a later ticket for ticket helpers (`TICKET HELPER.`) needs no mod change.

### 2. Matching (dashboard, `api.ts`)

A new `cleanTeamSnapshot(s, now)` cleans like `cleanSnapshot` (same row cleaning, same staleness and closing rules, same 24-hour cut-off) but keeps only snapshots whose cwd is **not** a worktree, and carries `threadId` (a string of at most 200 characters from `[A-Za-z0-9:%._-]`, else `null`) and `heading` (at most 40 characters, else `null`). `cleanSnapshot` is unchanged, so a worktree session can never reach this tab and a root session can never reach the Ship loop tab.

Each kept snapshot gets a role, checked in this order:

| Rule | Role |
|---|---|
| `sessionId` equals state `chiefSessionId`, or `threadId` equals state `chiefThreadId` | `chief` |
| `heading` is `BACKLOG RANKING` | `ranking` |
| `heading` is `PROJECT MANAGER HYGIENE` | `hygiene` |
| anything else | dropped |

When more than one snapshot is `chief`, the newest `updatedAt` wins (one card, one current session).

### 3. API

`buildApi` adds two keys; `status` and `merged` don't change.

- `chief`: `{ state: 'running' | 'idle' | 'paused', threadLink?: string, gantt?: Session[] }`.
  - `paused` when state `paused` is `true`. Else `running` when the matched session has an open last segment on its `main` row or on any `main:task:N` row (a turn is in progress; real snapshots carry the task rows only) and `updatedAt` is within 60 seconds. Else `idle`.
  - `threadLink` is `<t3-thread://v2/<environmentId>/<chiefThreadId>>`, built the way ticket rows build theirs.
  - `gantt` is the matched session alone. No matched session: no `gantt`.
- `pm`: a list, newest `updatedAt` first, each `{ sessionId, role: 'ranking' | 'hygiene', state: 'running' | 'finished', threadLink?: string, gantt: Session[] }`. `running` uses the same test as the card; otherwise `finished`. `threadLink` uses the snapshot's `threadId`. Live snapshots and history entries are merged by `sessionId`, the newer one wins.

### 4. History

`gantt-history.json` entries become `{ ticket, session }` (as today) or `{ role, session }` with `role` one of `ranking`, `hygiene`. `session` keeps `threadId` when it has one. `parseHistory` accepts both shapes and drops anything else, so an old file reads as before and a bad entry is skipped. Project manager entries have their own cap of 50, so they never push ticket sessions out of the 500. The server's 30-second loop records them next to the ledger sessions. A history session is shown as finished, as for merged tickets.

The Chief of Staff's own sessions are not kept in history: the card shows the current session only.

### 5. Page

- Under the header (title and call-to-action badges, which stay on both tabs) and the error line, two tab buttons: `Ship loop` and `Chief of Staff` (`role="tablist"`, `role="tab"`, `aria-selected`, arrow keys move between them).
- **Ship loop** holds `#status`, the `Merged` heading and `#merged`, as today.
- **Chief of Staff** holds:
  - A card: `Chief of Staff`, a state badge (`running`, `idle`, `paused`), a `Thread` link when there is one, and the gantt through the existing `renderGantt`. No session: `No Chief of Staff session in the last 24 hours.` under the title.
  - A `Project manager` heading and one row per `pm` entry: role label (`Backlog ranking` or `Hygiene`), state badge, `Thread` link, updated time, and the gantt in a `<details>` that opens the same way a ticket's gantt does. Ten per page with the Merged list's pager. Empty list: `No project manager threads yet.`
- The selected tab is saved in `localStorage` under `dashboard-tab` and restored on load. A missing or unknown value opens Ship loop. The poll keeps updating both tabs, so switching shows current data at once.

## Leaves out

- Ticket helpers and observation helpers on this tab (a later ticket; the heading field already makes them matchable).
- Retired Chief of Staff threads and their sessions.
- Spend or cost totals for the Chief of Staff or the project manager in the spend ledger. The gantt shows each session's own cost as it does today.
- Any change to the Ship loop tab, to how the Chief of Staff records threads, or to state.
- Backfilling the ~67 root-checkout snapshots already on disk: they have no heading, so only the one matching `chiefSessionId` shows.

## Calls I made (surprising first)

- **The agent-gantt mod changes**, so the Chief of Staff tab's project manager list fills only after the mod is updated on the machine (`/plugin` update) and a new ranking or hygiene child runs. Until then the list says `No project manager threads yet.` The Chief of Staff card works without the mod update, through `chiefSessionId`.
- **Roles come from the first prompt's heading, not from state.** The ticket offered a field from `writeSnapshot`, a state record, or the thread id. A state record would change the Chief of Staff skill and `cos_state.py`, which this ticket keeps out of scope. The heading needs only the mod, and the task headings are fixed text in `project-manager/reference.md`. If those headings change, the dashboard's two-row table must change with them.
- **The mod reports a generic heading, not a role.** The mod stays free of team words, and the dashboard holds the mapping.
- **The Chief of Staff is matched by `chiefSessionId` first, `chiefThreadId` second.** `chiefSessionId` is set on every plain Chief of Staff run and works for snapshots written before this change. Right after a rotation it is `null` until the new thread's first check, so the thread id covers that gap.
- **Running means a turn is open now** (open `main` or `main:task:N` segment and an update in the last 60 seconds). An idle Chief of Staff waiting for a notice shows `idle`, which is most of the time.
- Project manager history is capped at 50 entries, separate from the 500 ticket sessions.
- Ten project manager rows per page, using the Merged pager.
- The tab choice lives in `localStorage`, not the URL, so the T3 preview tab keeps it across reloads and restarts without a changed address.
- A thread id that has characters outside `[A-Za-z0-9:%._-]` or is longer than 200 is dropped, so nothing odd reaches the `t3-thread://` link.

## Tests

- `api.test.ts`, one table-driven test for the role rule: a root snapshot matching `chiefSessionId`, one matching only `chiefThreadId`, a `BACKLOG RANKING` heading, a `PROJECT MANAGER HYGIENE` heading, an unknown heading, and a worktree snapshot with a project manager heading (stays off the tab and on its ticket row). Includes a malformed snapshot (rows not a list, bad `threadId`, heading not a string) that is skipped without breaking `chief` or `pm`.
- `api.test.ts`, one test for `chief.state` (`paused`, `running`, `idle`) and the newest-first `pm` order with a live snapshot and its older history copy merged.
- `history.test.ts`, one test: a file with ticket entries, role entries and bad entries parses to the good ones; recording 51 project manager sessions keeps 50 and no ticket session is dropped.
- `snapshot.test.ts` (mod), one table-driven test for the heading pick: a delegated task with T3's first line, a `TEAM MODE.` task, a prompt with no heading, a heading on line 6 (not taken).
- `app.test.js`, one test that the Chief of Staff tab renders the card, an empty list message, and escapes a role row's fields; and that an unknown saved tab opens Ship loop.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.

Proved by hand in the PR: a dashboard run from the worktree shows both tabs; the Chief of Staff card shows the live Chief of Staff gantt; after a ranking child runs with the updated mod it appears in the list and stays after it finishes; a reload keeps the chosen tab.
