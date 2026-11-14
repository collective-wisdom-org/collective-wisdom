# CW-298: Read the dashboard Todo and Backlog from Linear and Jira, not only GitHub Issues

**Status:** Draft
**Ticket:** [#298](https://github.com/collective-wisdom-org/collective-wisdom/issues/298)

## Goal

On a repo whose `Tracker` row is `linear` or `jira`, the dashboard's Todo and Backlog sections list the open Todo and Backlog tickets, with the same fields the GitHub read gives (id, title, priority, created time). Today they are empty there.

## Today

- `agent-team/scripts/dashboard/backlog.ts` `createBacklog` runs `gh issue list` once a minute. `server.ts` calls `backlog.want(titleCfg)`, and `titleCfg` is set only when `repo.isGithubIssues`, so on Linear and Jira `backlog.get()` is `[]` and `buildApi` builds no Todo or Backlog group.
- Linear and Jira are reached only through MCP tools (`trackers/linear.md`, `trackers/jira.md`). The dashboard is a Node server with no MCP access.
- The Chief of Staff already reads both lists through the tracker tools, at two points:
  - **Todo start** (`chief-of-staff` SKILL.md § Tick): one `list-tickets` for state Todo, fields `id, labels, priority, createdAt`, piped to `cos_todo.py`. It runs on a turn whose act plan prints `start-todo`, that is when a spec slot is free.
  - **Backlog ranking** (`project-manager/reference.md` § Ranking child): the ranking child lists the whole Backlog in its own thread and returns at most 5 ready and 5 held entries, which `cos_rank.py` saves as `pm.ranked`. The Chief of Staff thread itself lists the Backlog only in the exit-3 recount.
- Tickets in flight show on every tracker, from `.agent-team/state.json`, and `buildApi` already skips a Todo or Backlog ticket that is in state or in the merged list.

## Design

The source is a file the Chief of Staff writes, `.agent-team/tracker-lists.json`, holding the last Todo list and the last Backlog list it read, as the tracker returned them. The dashboard reads that file on Linear and Jira repos. GitHub keeps its own `gh issue list` read.

### 1. The file

```json
{
  "todo":    { "at": "2026-11-14T10:00:00Z", "list": [ <list-tickets entries, tracker shape> ] },
  "backlog": { "at": "2026-11-14T09:00:00Z", "list": [ ... ] }
}
```

Either key may be missing. Entries are stored as the adapter returned them (at most 250 per list); the dashboard reader does the parsing, so the tracker shapes are handled in one place.

### 2. Writer: `agent-team/scripts/cos_lists.py`

- `cos_lists.py <todo|backlog> [--file PATH] < list-tickets JSON`. stdin is a JSON list, or an object holding an `issues` or `tickets` list (the shapes `cos_todo.py` already accepts). `--file` defaults to `.agent-team/tracker-lists.json` under the repo root (`app_root.root()`, as `cos_state.py` does).
- It replaces that one key with `{ "at": <now, UTC, Z>, "list": <the first 250 entries> }`, keeps the other key as it was (a missing or unreadable file starts empty), and writes through a temp file and a rename. Nothing is written when `.agent-team` is not a real folder or the file exists and is not a regular file, as the dashboard's own `writeJson` does.
- Prints `lists: saved <kind> <n>` and exits 0. Exit 2 with `lists: cannot <what>` when stdin is not one of the shapes, or the write fails. A failure never stops the Chief of Staff's turn: the step that calls it goes on.
- It also exposes `save(kind, tickets, file)` for `cos_todo.py`.

### 3. When the Chief of Staff writes

- **Todo:** `cos_todo.py`'s first pass (the list alone) calls `cos_lists.save("todo", ...)` with the parsed list before it prints its `get` lines, on every tracker. A save failure is ignored and changes nothing in its output or exit code. The Todo start's `list-tickets` fields gain `title`. So the Todo list is saved on every turn that already reads Todo, with no new tracker call and no JSON piped twice.
- **Backlog:** on a `linear` or `jira` tracker, after each Backlog ranking (`project-manager/reference.md` § Ranking child, after step 3 whatever `cos_rank.py` returned) and on the `backlog` command, the Chief of Staff makes one `list-tickets` (scope <TEAM>, state Backlog, limit 250, fields `id, title, priority, createdAt`, with the adapter's author filter) and pipes it to `cos_lists.py backlog`. A failed read or a `lists: cannot` line adds the Cleanup line `Dashboard Backlog not saved: <one line>` and nothing else. On GitHub this step is skipped: the dashboard reads GitHub itself.
- `cos_lists.py` is added to the script list in `chief-of-staff` SKILL.md § Tools, and the file to the `.agent-team/` files the skills name (not to `state.json`, whose keys stay as they are).

### 4. Reader: `agent-team/scripts/dashboard/lists.ts`

`createTrackerLists({ read: () => string | undefined, now? })` returns `{ want(prefix: string | null), get(): BacklogItem[] }`, with the `BacklogItem` type from `backlog.ts`.

- `want(prefix)` re-reads the file at most once every 10 seconds. A read that fails (no file, not JSON, not an object) keeps the last good list. A `todo` or `backlog` key that is missing or not `{ list: [...] }` keeps that kind's last good items.
- Each entry gives one item, its state from the list it is in (`todo` gives `Todo`, `backlog` gives `Backlog`):
  - **id:** the first of `identifier`, `id` and `key` that matches `^<PREFIX>-\d+$` (Linear's `id`, Jira's `key`). No match drops the entry.
  - **title:** `title`, else `fields.summary` (Jira), cleaned as `backlog.ts` does (control characters to spaces, trimmed, cut to 200 characters).
  - **priority:** a `priority:<name>` label; else `priority` (or `fields.priority`) as a name, an object with `name` or `value`, or Linear's number 1 to 4 (0 is none). Names map case-insensitively: Urgent and Highest to `urgent`, High, Medium, Low, and Lowest to `low`. Anything else is `null`.
  - **createdAt:** `createdAt`, else `fields.created`, in milliseconds or `null`. Jira's `+0000` offset is read as `+00:00` before parsing.
  - An entry that is not an object, or repeats an id already taken in the same list, is dropped. An id in both lists is kept in Todo only.
- `get()` returns `[]` until `want` has had a prefix, and `[]` after `want(null)`.

### 5. Server wiring

In `server.ts` `api()`: when the project's tracker is not GitHub issues (`repo` known and `!repo.isGithubIssues`) and a prefix is read, `buildApi` gets `backlog: trackerLists.get()` after `trackerLists.want(prefix)`, reading `.agent-team/tracker-lists.json` through the same `readRegular` guard as `dashboard.json`. Otherwise it gets `backlog.get()` as today. `buildApi` is unchanged: the in-state and merged skips, the top 3 Backlog cut and the GitHub-only `Full backlog` link and issue links stay as they are.

### 6. Docs

- `docs/compatibility.md` Matrix 2: the `Dashboard Todo and Backlog list` row. If #300 has added it by then, update its Linear and Jira cells; if not, add the row. GitHub `🟢 works`; Linear `🟡 partial`: read from the Chief of Staff's last Todo read (a turn with a free spec slot) and last Backlog ranking, so it can lag the tracker (new gap, the next free number); Jira the same partial plus untested (G12); Azure DevOps not supported (G19). The new gap line links #298. "Last checked" moves to the date the PR is written. A gap from #300 for this row, if it exists, gets the same text.
- README.md § Local dashboard: the Not started sentence says that on Linear or Jira the two lists come from the Chief of Staff's last Todo read and Backlog ranking, with no `Full backlog` link.

## Leaves out

- Issue links, titles of in-flight rows and update order on non-GitHub trackers (G15), and the `Full backlog` link on Linear and Jira.
- Azure DevOps (G19). Checking Jira against a live site (G12).
- Any change to the GitHub read: `backlog.ts` and `backlog.test.ts` stay as they are.
- Any new tracker call on turns that don't already read Todo, or a Backlog read on turns that don't rank.
- The order the Chief of Staff or the ranking child starts tickets in.

## Calls I made (surprising first)

- **The lists are only as fresh as the Chief of Staff's last read.** Todo is saved when a turn reads Todo, which happens only when a spec slot is free; the Backlog is saved after each ranking, which runs only when the ranked queue runs dry or on `backlog`. While every lane is full, a ticket the user moves to Todo doesn't appear, and one moved away still shows, until the next read. A ticket that starts leaves the list at once, because it is in state. The compatibility cell says `partial` for this reason. A fresher list would need a tracker read on every turn, which costs tokens on every Chief of Staff turn.
- **The Backlog gets its own `list-tickets` after each ranking**, in the Chief of Staff thread, rather than reusing `pm.ranked` (only the top 5 ready and 5 held, so the heading count would be wrong) or having the read-only ranking child write a file.
- **`cos_todo.py` writes a file now.** Its docstring says it writes nothing; its first pass already holds the Todo list, so saving there costs no extra call and no second copy of the JSON. A save failure doesn't change its output.
- **The Todo list is saved on every tracker, GitHub included,** so the step has no tracker branch; the dashboard ignores the file on GitHub. The Todo `list-tickets` fields gain `title` everywhere.
- **The file holds tracker-shaped entries and the TypeScript reader parses them**, so the Linear and Jira shapes live in one tested place and the writer only checks the outer shape.
- **The reader re-reads the file at most every 10 seconds**, not once a minute like the GitHub read, because it is a local file.
- **An id in both lists shows in Todo only**, and a repeated id keeps its first entry.
- **The new file is not a `state.json` key**, because `state-keys.md` forbids new top-level keys and the dashboard is its only reader.
- **The compatibility row is shared with #300.** Whichever PR merges second updates the other's cell rather than adding a second row.

## Tests

Per `AGENTS.md` § Testing, one table per rule:

- `dashboard/lists.test.ts`: tracker shape in, items out. One table of Linear and Jira entries (id from `identifier`, `id` or `key`; Jira `fields`; each priority form; `+0000` dates) and bad ones dropped (wrong prefix, not an object, repeated id). A second test: Todo and Backlog states, an id in both kept in Todo, a failed or half-bad read keeps the last list, re-read at most every 10 seconds, `get()` empty for a null prefix.
- `test_cos_lists.py`: one table for the writer: each accepted stdin shape saves that key and keeps the other, a bad shape writes nothing and exits 2, at most 250 entries kept, a non-regular file is not written.
- `test_cos_todo.py`: one case that the first pass saves the Todo list and that a failing save leaves its output unchanged.
- `server.test.ts`: one case that a `linear` project serves the file's Todo and Backlog in `/api`.
- `backlog.test.ts` passes unchanged.

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` pass. A live Linear run goes under the PR's Not proven.

## Touches

None of data, money, auth, user email or migrations. A new file under `.agent-team/` that holds ticket ids, titles and priorities already in the tracker.
