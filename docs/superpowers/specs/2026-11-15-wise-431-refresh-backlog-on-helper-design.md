# WISE-431: Refresh the dashboard Backlog when a ticket helper files a ticket

**Status:** Draft
**Ticket:** [#431](https://github.com/collective-wisdom-org/collective-wisdom/issues/431)

## Goal

When a ticket helper files a ticket, the Chief of Staff refreshes the dashboard's ticket lists before it posts the helper's report, so the new ticket shows in the dashboard Backlog tab within seconds instead of on the next 60 second poll (GitHub) or the next unrelated Backlog save (Linear, Jira).

## Today

Facts from main at `a1ab8ed`.

- `chief-of-staff/ticket-helper.md` § Helper test reads the helper's `TICKET HELPER DONE` block and posts it under the `Tickets` report section. It runs no dashboard script.
- `chief-of-staff/commands.md`, the `mark N todo` / `move N to backlog` row, already defines the dashboard refresh: on `linear` or `jira`, pipe the Todo `list-tickets` to `cos_lists.py todo` and the Backlog one (`project-manager/reference.md` step 3, Dashboard save, with its author filter) to `cos_lists.py backlog`; on every tracker, run `cos_lists.py changed`. A failed read or a `lists: cannot <what>` line adds `Dashboard not refreshed: <one line>` to the reply.
- On GitHub, `cos_lists.py changed` sets the stamp that makes `createBacklog` in `agent-team/scripts/dashboard/backlog.ts` re-read the issues at once.
- The helper can't refresh itself: it writes only the tracker, and `cos_lists.py` writes `.agent-team/tracker-lists.json` in the root checkout.
- `chief-of-staff/SKILL.md` (the state file paragraph) lists who runs `cos_lists.py`; the helper test is not on it.

## Design

Markdown only. No script or dashboard code changes.

### `chief-of-staff/ticket-helper.md` § Helper test

Add one bullet after the first one (the read and post):

- When the block's `Tickets:` line lists at least one ticket (an observation helper and a `Request from` helper too), run the Backlog half of the dashboard refresh in the `mark N todo` row of commands.md § Commands before posting: on `linear` or `jira`, the Backlog `list-tickets` piped to `cos_lists.py backlog`; on every tracker, then `cos_lists.py changed`. The Todo list is not re-read, since a helper files into Backlog. If a read fails or a script prints `lists: cannot <what>`, add `- Dashboard not refreshed: <one line>` to the post; the ticket stands and the post goes out. `Tickets: none`, no marker, or a failed or interrupted run: no refresh.

The bullet points at the commands.md row and does not copy its commands.

The refresh runs on the helper's saved tickets, not on anything the block asks for, so it still runs when the block holds an instruction that bullet 3 ignores.

### `chief-of-staff/SKILL.md`

The state file paragraph's list of `cos_lists.py` callers ("also run by `cos_todo.py`'s first pass and by `cos_state.py apply` on a start, merge or drop") gains "and by the helper test (ticket-helper.md § Helper test)". It stays one parenthetical.

## Leaves out

- The dashboard server, `REFRESH_MS` and any faster tracker polling.
- Tickets created by hand or by other tools: they still wait for the GitHub poll.
- The Writing tickets placeholder row (WISE-430).
- Re-reading the Todo list after a helper.

## Calls I made

- Only the Backlog half of the refresh runs (`cos_lists.py backlog`, then `changed`), not `cos_lists.py todo`. A helper files into Backlog, so re-reading Todo is a wasted tracker call. The ticket says the same.
- The refresh runs when the block carries an instruction that the helper test ignores. Refreshing a list is not an action the block asked for, and the saved ticket is real either way.
- A `Request from` (cross-repo) helper also triggers the refresh, since it files in this repo's tracker.
- The `Dashboard not refreshed:` line goes in the post as a `- ` bullet like the helper test's other added lines, worded as in commands.md.
- `SKILL.md`'s list of `cos_lists.py` callers gets the helper test added, so that list stays true. The ticket didn't ask for this.

## Acceptance

- A helper whose block lists a ticket: the Chief of Staff runs `cos_lists.py changed` (with `cos_lists.py backlog` first on Linear or Jira) before posting, and the ticket appears in the dashboard Backlog tab within seconds.
- `Tickets: none`: no refresh.
- A failed refresh adds `Dashboard not refreshed:` and the report still posts.
- No dashboard code changes.
