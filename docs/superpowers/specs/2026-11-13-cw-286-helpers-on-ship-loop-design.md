# CW-286: Show ticket helpers on the Ship loop tab and count their time in the ticket gantt

**Status:** Shipped
**Ticket:** [#286](https://github.com/collective-wisdom-org/collective-wisdom/issues/286)
**Shipped:** in PR #289, with differences: [as-built](../as-built/2026-11-13-cw-286-helpers-on-ship-loop-as-built.md)

## Goal

A ticket helper stops being a separate list on the Chief of Staff tab. While it runs it is an In progress card on the Ship loop tab. Once it files a ticket, its session belongs to that ticket: the ticket shows in a new Backlog or Todo section (or wherever its stage puts it), and its gantt and spend start with the helper, then Spec, Build and the rest.

## Today

- The agent-gantt mod writes one snapshot per session to `.agent-team/gantt/<session>.json` with `threadId` and `heading` (`buildSnapshot` in `mods/agent-gantt/hooks/snapshot.ts`). The heading comes from the first task prompt (`pickHeading`). Nothing in the snapshot says which ticket a helper filed.
- The mod's `turn.complete` hook already runs on every main-loop turn. Its event carries `answer`, the assistant's final visible text of the turn, which the mod does not read today.
- `buildApi` (`agent-team/scripts/dashboard/api.ts`) puts root-checkout sessions with heading `TICKET HELPER` into `Api.helpers`; `renderChief` (`page/app.js`) draws them as the Ticket helpers list. `history.ts` keeps the newest 50 helper sessions as `{ role: 'helper' }` entries.
- Ship loop rows come only from `state.tickets` (`groupTickets`), so a Backlog or Todo ticket is not on the tab. A row's gantt is the live worktree sessions whose branch matches the ticket (`ticketOf`); a merged ticket's gantt and spend come from `gantt-history.json` and `spend.json`, both fed by `ledgerSessions`.
- The dashboard's only tracker read is titles, through `gh.sh` (`titles.ts`, `ghRunner`).

## Design

### 1. The mod records the filed ticket (`mods/agent-gantt/hooks/`)

- On a main-loop `turn.complete`, when the session's heading is `TICKET HELPER` and `answer` holds a line `TICKET HELPER DONE`, the mod reads the `Tickets:` line and the lines under it up to the next `Key:` line, and takes the first `<PREFIX>-N` id at the start of a ticket line (`CW-12: title, URL`). That id is the session's ticket, kept in a new atom and written to the snapshot as `ticket` (null until found, and null for `Tickets: none`). A pure function in `snapshot.ts` does the parse so it is testable.
- Once set, the ticket does not change for the session.
- The mod also writes `request`: the first non-empty line after `The user's request, verbatim:` or `The Chief of Staff's observation:` in the first task prompt of a `TICKET HELPER` session, whitespace collapsed, cut to 80 characters; null otherwise. It is the placeholder card's title.
- The Cursor hook is not changed: a helper run on Cursor shows its placeholder card while it runs, but its session is not attached to a ticket.

### 2. Matching helper sessions (`api.ts`)

- `cleanTeamSnapshot` reads `ticket` (kept only when it matches `^<prefix>-\d+$` for the project's prefix) and `request` (a string of at most 80 characters, else null).
- A helper session with a ticket belongs to that ticket. `ledgerSessions` returns it alongside the worktree sessions, so the server records it in `spend.json` and as a ticket entry in `gantt-history.json`, exactly like a Spec or Build session. A merged ticket's gantt and spend then include it with no other change.
- A helper session without a ticket shows only while running (the existing running test: an open main turn updated in the last 60 seconds). Running, it is a placeholder row; finished, it shows nowhere. A helper that fails or files nothing therefore leaves no card.
- `teamSessions` and `Api.pm` keep the ranking and hygiene threads only. `Api.helpers` is removed.

### 3. Backlog and Todo from the tracker (new `backlog.ts`)

- Only when the tracker is `github` and the repo slug is known. Other trackers get no Backlog or Todo section.
- Once a minute, in the background like `titles.ts`, the server runs `gh.sh issue list --repo <slug> --state open --limit 200 --json number,title,labels,author`. An issue with `status:todo` is Todo; one with no `status:` label is Backlog; any other is skipped. Order is the tracker's (newest first).
- Team tickets only, per the GitHub adapter: an issue counts only when its author's `collaborators/<login>/permission` `role_name` is `triage`, `write`, `maintain` or `admin`. The answer is cached per login for the life of the server. An issue from anyone else is not listed.
- A failed read keeps the last good list; titles are cleaned like `titles.ts` does.
- An issue already in `state.tickets` or in the merged list is skipped, so a ticket shows in one place.

### 4. The API rows

- Two new groups after the state groups: `Todo` then `Backlog`, each row `{ id, title, issueUrl, risk: '', next: '', stage: '' }`.
- A new group `Writing tickets` holds one placeholder row per running helper with no ticket: `{ id: 'helper:<sessionId>', title: <request or ''>, helper: true, threadLink?, gantt: [session] }`, newest first.
- Every ticket row, in any group, gets its helper sessions: live ones from the snapshots and finished ones from the history, merged by `sessionId` (the live copy wins), added to its `gantt`, which stays sorted oldest first. So the helper bar comes before Spec and Build.

### 5. Page (`page/app.js`)

- `Writing tickets` sits in the In progress band (an unknown group already goes there). A placeholder card shows `Ticket helper` where the id goes, the request line as its title, the `Copy thread link` button and its `Agents` chart, and no issue link or Details.
- A new band `Not started` after Queued holds `Todo` then `Backlog`, as flat rows like Queued, with the existing collapse that the page remembers.
- `renderChief` drops the Ticket helpers heading, its pager (`data-helper-page`, `helperPage`) and its charts (`data-helper`). `ROLE_LABELS` loses `helper`.
- The `No state yet` message shows only when there are no groups at all, Backlog and Todo included.

### 6. History (`history.ts`)

- `ROLES` drops `helper`, and `build` drops the separate 50-session helper cap. Old `{ role: 'helper' }` entries in `gantt-history.json` are dropped on the next read. A helper attached to a ticket is a ticket entry under the existing 500-session cap.

### 7. README

README.md § Local dashboard: the Ticket helpers list paragraph goes; it says where a running helper shows, the Backlog and Todo sections (GitHub tracker only, team tickets only, refreshed once a minute), and that a filed ticket's gantt and spend start with its helper.

## Leaves out

- Ranking or filtering Backlog and Todo beyond tracker order, and dropping epics from them.
- Backlog ranking and hygiene threads, which stay in the Project manager list.
- Attaching a helper's session to a ticket on Cursor, and Cursor spend (#284).
- Backfilling helper sessions already on disk: they carry no `ticket`, so they attach to nothing.
- Any change to the Chief of Staff, the ticket helper prompt, or state.

## Calls I made (surprising first)

- **The mod learns the ticket from the helper's `TICKET HELPER DONE` block**, read off `turn.complete`'s `answer`, and writes it into the snapshot. The ticket offered this or an issue number in the output; the block is the stable, documented contract, and the dashboard has no other way to see the helper's output.
- **Several tickets: the first one gets the whole session.** No split of time or cost across tickets.
- **Backlog and Todo list every open team ticket in those states, not just the ones a helper filed**, up to 200 open issues. That is what a Backlog section means, and it is how a ticket filed by hand shows too.
- **A new `Not started` band** after Queued for Todo and Backlog, as flat rows, rather than adding them to Queued, which means "will start soon".
- **Issues from authors without triage or higher are not listed**, following the GitHub adapter's team-ticket rule, with the permission answer cached per login.
- **Every ticket row gets its helper sessions from history too**, not just Backlog and Todo, so a ticket already in Spec or Build still opens with its helper bar after the live snapshot ages out.
- **Old helper history entries are dropped**, not kept or converted: they have no ticket to attach to and the list that showed them is gone.
- A finished helper that filed nothing leaves no trace on the page; the Chief of Staff's report still says `Ticket helper ended without a report`.
- The tracker is read once a minute, not on every page poll.
- The placeholder's title is the first line of the user's request (or the observation), since the snapshot has no thread title.

## Tests

- `mods/agent-gantt/hooks/snapshot.test.ts`: one table for the done-block parse (one ticket, several, `none`, no block, a block from a non-helper heading) and the request line.
- `api.test.ts`: one table for where a root `TICKET HELPER` snapshot lands (running without ticket: `Writing tickets`; finished without ticket: nowhere; with ticket on the board: in that row's gantt before the worktree sessions; with ticket in history only: same), plus the Backlog and Todo rows skipping a ticket in state.
- `backlog.test.ts`: the issue list parse into Todo and Backlog with an untrusted author dropped and a failed read keeping the last list.
- `history.test.ts`: an old `helper` role entry is dropped; the helper cap test goes.
- `page/app.test.js`: a placeholder card in In progress and Todo and Backlog rows under Not started, fields escaped; the Chief of Staff tab has no Ticket helpers list.

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` pass. A hand run of the dashboard with a live helper goes under the PR's Not proven.
