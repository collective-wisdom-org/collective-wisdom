# CW-355: Remove a ticket from the dashboard Todo list when it leaves Todo

**Status:** Shipped
**Shipped:** in PR #381, with differences: [as-built](../as-built/2026-11-14-cw-355-todo-list-stale.md)
**Ticket:** [#355](https://github.com/collective-wisdom-org/collective-wisdom/issues/355)
**Related:** #347

## Goal

In a Linear or Jira repo, a ticket the team starts, merges or drops leaves the dashboard's Todo list at once, and a Todo list that has not been read from the tracker for a while says how old it is and looks it.

## Today

Facts from main at `81c114b`.

- `cos_todo.py` (first pass) saves the Todo list with `cos_lists.save("todo", text)`. `project-manager` saves the Backlog list with `cos_lists.py backlog` after each ranking. Both write `.agent-team/tracker-lists.json` as `{"todo": {"at", "list"}, "backlog": {"at", "list"}}`.
- Nothing else rewrites that file. The `start`, `merged` and `drop` ops in `cos_state.py` leave it alone, and so does a move the user makes in the tracker.
- `createTrackerLists` in `dashboard/lists.ts` re-reads the file every 10 seconds and ignores `at`.
- `buildApi` in `dashboard/api.ts` hides a Todo or Backlog entry whose id is in `state.json` or the merged list. Once the ticket leaves both (after `drop`, after `prune` ages it out of `merged`), the stale entry shows again.
- The GitHub Issues path reads the tracker live and is not affected.

## Design

Two of the ticket's three fixes: the first (it fixes the cause for every change the team makes) and the second (it covers a change the team does not see, such as a move the user makes in the tracker).

### 1. State ops drop the ticket from the saved lists

- `cos_lists.py` gets `remove(ids, file=None)`. It drops every entry whose id is in `ids` from both the `todo` and the `backlog` list, keeps each list's `at` as it was (the rest of the list is no fresher than before), and writes the same way `save` does: the same folder and regular-file checks, temp file and rename. An absent file, an absent kind or no matching entry writes nothing. It raises `Cannot` on a failed write, like `save`.
- The id of an entry is read the way the dashboard reads it: `identifier`, then `id`, then `key`.
- `cos_state.py apply`: after a successful apply, it collects the ticket ids named by every `start`, `merged` and `drop` op in the batch and calls `cos_lists.remove(ids, file=<state file's folder>/tracker-lists.json)`. So `--file` in a test points both files at the same temp folder.
- A failure there never changes the apply result: the state is already saved, the output (`unchanged` or `saved` and its lines) and the exit code stay exactly as today, and the error is ignored. It runs on `unchanged` too, so a repeat `merged` op still clears a stale entry.
- `start` covers the Chief of Staff starting a Todo ticket (readiness.md § Todo start ends in a `start` op) and a Backlog pick. `merged` covers a merge. `drop` covers a cancel.

### 2. The dashboard shows the list's age

- `createTrackerLists` keeps each kind's `at` (parsed to ms, or null when missing or bad) next to its items, and `get()` gives each item a `readAt`.
- `buildApi` puts `readAt` on the Todo and Backlog groups of a Linear or Jira repo (the GitHub path has none) and `stale: true` when `now - readAt` is over one hour.
- The page, for a group with `stale`, adds a line under the group title: `Read from the tracker 3h 16m ago`, using the same duration words as the `waiting` counter, and greys the group's rows (the existing `--muted` colour, with the `.stale` class). A fresh list shows no line. A group with no `readAt` (an old file without `at`) shows no line either.

## Leaves out

- Fix 3 (reading Todo on every tick). The Chief of Staff acts only when woken, so a tick-time read would still not run on a quiet team, and it adds a tracker call to every tick.
- A move the user makes in the tracker is still only fixed by the next Todo pass; the age line is what makes it visible meanwhile.
- `cos_todo.py`'s silent `except Exception: pass` on the save stays: a failed save keeps the old list, and the age line now shows it.
- The GitHub Issues path.
- How the Chief of Staff ranks or starts Todo tickets.
- Reinstalling consuming repos (each does it in its own ticket PR).

## Tests

- `test_cos_state.py` (or `test_cos_lists.py`): one table-driven test. For each of `start`, `merged` and `drop`, a lists file holding the ticket in Todo and in Backlog plus another ticket; after `apply`, the named ticket is gone from both lists, the other stays, and both `at` values are unchanged. One more row: the lists file is a link or missing, and `apply` still exits 0 with its usual output.
- `lists.test.ts` / `api.test.ts`: one table test for the age: `at` an hour and a minute old gives `stale: true` and the `readAt`; ten minutes old gives no `stale`; no `at` gives neither.
- `app.test.js`: a stale group renders the age line; a fresh one does not.

## Docs to update

- `cos_lists.py` and `cos_state.py` docstrings.
- `chief-of-staff/SKILL.md` and `org-chart.md` say only `cos_lists.py` writes `tracker-lists.json`. That stays true (`cos_state.py` writes through it), but the lines name `cos_todo.py` as the other caller; add `cos_state.py apply`.

## Calls I made

- One hour is the age where the Todo list counts as stale and shows its age. The ticket did not set a number. The Chief of Staff has no timer, so on a quiet team a list an hour old is normal; an hour is long enough not to nag after every pass and short enough to show a day-old list.
- Fixes 1 and 2, not 3 (reasons under Leaves out).
- A state op removes the ticket from the Backlog list as well as Todo. The ticket names Todo, but a Backlog pick goes stale the same way and the file is the same.
- The age line and the grey rows apply to the Backlog group too, for the same reason.
- Removing an entry keeps the list's `at`: it was read from the tracker then, and the rest of it is no fresher.
- A failed removal is silent and never changes `cos_state.py`'s output or exit code, so no Chief of Staff pass breaks on it.
- Removal runs on every successful apply that names one of the three ops, including one that prints `unchanged`.
