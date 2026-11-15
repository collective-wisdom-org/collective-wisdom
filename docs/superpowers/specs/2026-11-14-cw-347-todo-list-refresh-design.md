# CW-347: Show a ticket on the dashboard Todo list as soon as the Chief of Staff marks it Todo

**Status:** Shipped
**Shipped:** in PR #356, as specified
**Ticket:** [#347](https://github.com/collective-wisdom-org/collective-wisdom/issues/347)
**Related:** [#345](https://github.com/collective-wisdom-org/collective-wisdom/issues/345) (building on `dashboard/page/app.js` now; this ticket changes one line there)

## Goal

When the user asks the Chief of Staff to mark a ticket Todo, or move one back to Backlog, the dashboard shows the change within a few seconds, with no Chief of Staff pass in between, on GitHub, Linear and Jira. A failed tracker read shows on the page instead of being dropped.

## Today

Facts from `main` at `6e85821`.

- **GitHub.** `createBacklog` (`agent-team/scripts/dashboard/backlog.ts`) runs `gh issue list` and reads the `status:` labels itself. `want()` starts a read only when the last one started at least `REFRESH_MS` (60 s) ago. A failed read is swallowed (`catch {}`) and the last list stays. The page polls `/api` every 5 s.
- **Linear and Jira.** `createTrackerLists` (`dashboard/lists.ts`) reads `.agent-team/tracker-lists.json` at most every 10 s. Only `cos_lists.py` writes that file: `cos_todo.py`'s first pass saves the Todo list, and the project-manager ranking saves the Backlog list (`project-manager/reference.md` step 4, Dashboard save). A state change the Chief of Staff makes on request saves nothing, so the list stays old until the next pass. A bad file is also swallowed.
- **How the Chief of Staff marks a ticket.** A plain "mark N as todo" has no row in `chief-of-staff/commands.md`; the Chief of Staff runs the adapter's `set-state` and stops. `cancel N` also moves a ticket to Todo.

### The cause, confirmed

The user saw the stale view in this repo, which is on GitHub, so `tracker-lists.json` played no part. From the issue events and the Chief of Staff thread:

| Ticket | `status:todo` added (UTC) | User reports the stale view | Gap |
|---|---|---|---|
| CW-343 | 02:09:27 | 02:10:19 | 52 s |
| CW-341 | 02:09:44 | 02:10:19 | 35 s |
| CW-342 | 02:09:46 | 02:10:19 | 33 s |

Every gap is under the 60 s refresh, so the refresh alone explains what the user saw: a label change waits up to 60 s for the next read, plus up to 5 s for the next page poll. A failed read would make it longer, not shorter, and nothing points to one here. The fix still makes failed reads visible, as the ticket asks.

## Design

### A change stamp the Chief of Staff writes

- `cos_lists.py changed` (no stdin) sets a top-level `"changed": "<now, UTC>"` in `tracker-lists.json` and keeps the `todo` and `backlog` lists as they are. It prints `lists: saved changed` and exits 0, or exit 2 with `lists: cannot <what>`, with the same folder and regular-file checks and temp-file rename as a list save.
- The dashboard reads the stamp on every tracker: on GitHub it means "read the issues again now", and on Linear and Jira it is ignored (the saved lists are the change).

### The Chief of Staff, on a state change the user asks for

One new row in `chief-of-staff/commands.md`, which is outside the size-limited core of `SKILL.md`:

- **`mark N todo`, `move N to backlog`, or any other request to set a ticket to Todo or Backlog:** run `set-state`, then the dashboard refresh. On `linear` or `jira`, save both lists first: the Todo list with the same `list-tickets` call § Todo start makes (state Todo, fields `id, title, labels, priority, createdAt`) piped to `cos_lists.py todo`, and the Backlog list with the call in `project-manager/reference.md` step 4 piped to `cos_lists.py backlog`. Then, on every tracker, run `cos_lists.py changed`. A failed read or a `lists: cannot` line goes in the reply as `Dashboard not refreshed: <one line>`; the state change stands.
- The `cancel N` row gains "then the dashboard refresh (the mark-N row)".
- `session.md`'s script list names `cos_lists.py changed`. `SKILL.md` is not touched.

### GitHub: re-read on a new stamp

- `server.ts` reads `tracker-lists.json` for the stamp on every tracker. `lists.ts` gains a `changed()` getter for it; `want(null)` (GitHub) still reads the file for the stamp, but keeps no lists.
- `createBacklog.want(cfg, changed)` starts a read at once when `changed` differs from the stamp it last saw, even inside the 60 s. If a read is already running, it runs one more read right after, because the running one may have started before the label changed. The first stamp it sees counts as seen, so a server start does not cost an extra read.
- The 60 s background refresh stays as it is, for changes the user makes on GitHub directly.

### Linear and Jira: a faster file read

- `lists.ts` re-reads the file at most every 1 s instead of 10 s. It is a small local file, so the cost is nothing, and the saved lists then reach the page within about 6 s (1 s plus the 5 s poll).

### A failed read shows on the page

- `createBacklog` keeps an `error()`: set when `gh issue list` fails or its output is not a list, cleared on the next good read. The text is `Could not read Todo and Backlog from GitHub: <reason>. Showing the last list read.` The reason is the first line of the error, with control characters stripped, cut to 120 characters.
- `createTrackerLists` keeps an `error()` too: set when the file exists but is not JSON, or its `todo` or `backlog` key is not `{ list: [...] }`; a missing file is not an error. Text: `Could not read the saved Todo and Backlog lists: <reason>. Showing the last list read.`
- `/api` gains `trackerError` (string or null), from whichever reader the tracker uses.
- `page/app.js` shows it in the existing `#error` line beside `restartError`: one line, `err.textContent = [last.restartError, last.trackerError].filter(Boolean).join(' ')`. The build rebases on `main` before it touches `app.js`, because CW-345 is changing that file.

### Tests

- `backlog.test.ts`, one table-driven test: a new stamp reads at once; the same stamp does not; a new stamp during a read runs one more read after it; a failed read sets `error()` and keeps the list; a good read clears it.
- `lists.test.ts`: the stamp is read on GitHub and Linear/Jira alike; a bad file sets `error()`, a missing file does not.
- `test_cos_lists.py`: `changed` writes the stamp and keeps both lists, and refuses a linked file like a list save.
- No test for the one `app.js` line (AGENTS.md § Testing).

## Leaves out

- Which tickets count as Todo or Backlog, and how the lists are ordered (ticket's Out of scope).
- A shorter GitHub background refresh. It would add a `gh issue list` call every few seconds while the dashboard runs, on the same account the team uses, to catch changes that the stamp already catches.
- State changes the user makes in the tracker by hand. They still show within 60 s on GitHub and at the next pass on Linear and Jira.
- Other state changes the Chief of Staff makes (start, In Review, Done). A started ticket already shows from `state.json`, not from the Todo list.

## Not proven before merge

- The Linear and Jira path end to end: this repo is on GitHub, so the Chief of Staff's list saves there are checked only by the `cos_lists.py` tests and by reading the new row.
- That the Chief of Staff follows the new row in a live session; the build checks the row's wording, not a run.

## Calls I made

- **The GitHub fix is a re-read on a stamp the Chief of Staff writes, not a shorter refresh.** The ticket allowed either. The stamp shows the change within one page poll plus one `gh issue list` (a few seconds) and adds one call per state change instead of one every few seconds.
- **The stamp lives in `tracker-lists.json`,** the file `cos_lists.py` already owns and the Chief of Staff may already write, so no new file and no new write permission.
- **`app.js` changes by one line** to show the failed-read message in the existing error line. Putting the message into `restartError` instead would avoid the page file but mislabel it.
- **`cancel N` also refreshes the dashboard,** since it moves a ticket to Todo on the user's request.
- **Linear and Jira save both lists on every such change,** so a ticket moving either way lands in the right list. Saving only the Todo list would leave a ticket moved back to Backlog missing from Backlog until the next ranking.
- **The Linear/Jira file read drops from 10 s to 1 s.** The ticket did not ask for it, but at 10 s the saved change could take 15 s to show, which is not "a few seconds".
- **The CoS change goes in `commands.md`, not `SKILL.md`.** The `SKILL.md` core is at 17,952 of its 18,000 bytes.
