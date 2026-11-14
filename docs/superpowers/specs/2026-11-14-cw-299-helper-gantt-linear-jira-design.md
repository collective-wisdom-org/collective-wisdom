# CW-299: Show a ticket helper's session on the gantt for a ticket in Linear or Jira

**Status:** Draft
**Ticket:** [#299](https://github.com/collective-wisdom-org/collective-wisdom/issues/299)

## Goal

On a Linear or Jira repo, a ticket helper's session shows on the gantt of the ticket it filed as soon as that ticket is in the dashboard's Todo or Backlog list, live and from history, as it does on GitHub.

## Today

- `buildApi` (`agent-team/scripts/dashboard/api.ts`) adds a helper session to a ticket's gantt only when the ticket has a board row (`addHelper` checks `rowById.has(ticket)`). It does this for the live snapshot (`team` items with `role === 'helper'` and a `ticket`) and for history (`history[id]` sessions whose `cwd` is not a worktree).
- Since CW-298 (PR #303), `server.ts` feeds `buildApi` the Todo and Backlog of a Linear or Jira repo from `.agent-team/tracker-lists.json` through `lists.ts` `createTrackerLists`. Those items become Todo and Backlog rows, so `rowById` now holds a just-filed Linear or Jira ticket once the Chief of Staff has saved a list with it. Nothing in `addHelper`, `cleanTeamSnapshot` or `ledgerSessions` depends on the tracker.
- So the code path the ticket asks for should already work. What is missing is a test that proves it with Linear and Jira shaped ids, and the compatibility doc still says the session shows only once the ticket is in state (G23).
- Ticket key shapes: `pickFiledTicket` (`mods/agent-gantt/hooks/snapshot.ts`) reads `[A-Z][A-Z0-9]*-\d+`, `prefixFromProject` (`titles.ts`) reads `[A-Za-z][A-Za-z0-9]*`, and `cleanTeamSnapshot` builds `^<prefix>-\d+$` from that prefix. None accepts `_`. The Python side agrees: `project_config.py` and `setup_repo.py` accept a prefix only if it matches `[A-Z][A-Z0-9]*`.
- Jira project keys: Jira Cloud requires an uppercase letter followed by uppercase letters or digits; it rejects `_` and `-`. Jira Data Center defaults to `([A-Z][A-Z]+)` and lets an admin change the key pattern to one that allows `_` (Atlassian, "Changing the project key format").

## Design

### 1. The test (`agent-team/scripts/dashboard/api.test.ts`)

One table-driven test, `a helper session joins its filed ticket's Todo or Backlog row on Linear and Jira`. Each case:

- builds the Todo and Backlog items through `createTrackerLists` from a `tracker-lists.json` text in the tracker's own shape: Linear (`identifier: 'ENG-12'`, `title`, numeric `priority`, ISO `createdAt`) and Jira (`key: 'PROJ-7'`, `fields.summary`, `fields.priority.name`, `fields.created` with a `+0000` offset);
- calls `buildApi` with `repo: { url, isGithubIssues: false }`, that prefix, those items, and a root checkout `TICKET HELPER` snapshot whose `ticket` is the row's id;
- checks the session id is in that row's `gantt`.

Rows: Linear Backlog, Jira Backlog, Jira Todo (live snapshot), and one row per tracker where the snapshot is gone and the session comes only from `history[id]`. One more row: a Linear ticket that the saved lists do not hold puts the session nowhere (the G22 lag, kept on purpose).

If the test fails, the fix goes in `api.ts` (or `lists.ts`) in this PR. I expect it to pass on main as is.

### 2. Underscore keys: not accepted

`pickFiledTicket`, `prefixFromProject` and `cleanTeamSnapshot` stay as they are. The PR body says why: Jira Cloud does not allow `_` in a project key; Jira Data Center allows it only after an admin changes the key pattern, and the team's own config reader (`project_config.py`) and setup (`setup_repo.py`) already refuse such a prefix, so the dashboard and the mod accepting it would change nothing. A new gap line records the Data Center case.

### 3. `docs/compatibility.md`

- Matrix 2, "Ticket helper in the gantt": Linear becomes `🟢 works`, with the note that the row comes from the Chief of Staff's last saved list (G22). Jira becomes `⚪ untested: same code as Linear (G12)`, the wording the other Jira cells use for code never run against Jira.
- Drop G23 and its reasons, per the doc's rule for a cell that moves to `works`. Reword the "Ticket helper in the gantt" note under Matrix 2 to say the session joins the ticket's row once the ticket is in the saved Todo or Backlog list or in state, and drop the "(G23)" pointer in the Matrix 1 note.
- New gap G24: a Jira Data Center site whose admin allows `_` in project keys cannot use the team, because `project_config.py`, `setup_repo.py`, the dashboard and the `agent-gantt` mod read a prefix as letters and digits only. Ticket: none yet. It hangs on the Jira column's Setup row.
- Rebase on main before editing, since CW-300 and CW-302 also edit this file.

## Leaves out

- Any change to how fresh the Linear and Jira lists are (G22, CW-298's ticket).
- The Backlog shows only its top 3 rows (CW-296). A helper whose ticket ranks below that has no row and stays off the chart until the ticket moves up or into state. This is the same on GitHub and is not a tracker gap; spend still attaches.
- A `Writing tickets` card for a finished helper.
- Accepting `_` in a ticket key anywhere (see Design 2).
- Azure DevOps (G19).
- No change to the `agent-gantt` mod, so no plugin version bump.

## Calls I made (surprising first)

- No runtime code change unless the new test fails: CW-298 already gives Linear and Jira tickets their board rows, and the helper path never looked at the tracker.
- Underscore keys stay rejected, and the PR says Jira doesn't allow them (Cloud) or allows them only by admin change (Data Center), with a new gap G24, rather than widening three regexes while the Python config reader still refuses the prefix.
- The test builds its rows through `createTrackerLists` from tracker-shaped JSON rather than hand-written `BacklogItem`s, so it covers the CW-298 read and the helper join together, as the ticket's "a Backlog row from the new read" asks.
- Linear's cell goes to `works` with the G22 lag noted, not `partial`: the remaining delay is the list's freshness, which G22 already tracks. Jira goes to `untested` like its other cells.
- The top-3 Backlog cutoff is left as is and called out here, not filed: it is the same on every tracker.

## Tests

- The one table-driven test above, in `api.test.ts`, run with `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` (Node 24 or newer), plus the repo test command.

## Touches

None of these (no data, money, auth, user email or migrations).
