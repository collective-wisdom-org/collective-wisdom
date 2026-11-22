# Linear adapter

How each operation in [README.md](README.md) runs on Linear, through the Linear MCP (the default tracker). `<TEAM>` is the team in `project.md` § Identity (`Linear team name`); `Linear project`, if set, narrows it.

## Rules

- `list_issues` and `get_issue` always pass `fields`, with only what the step uses. Ask for `description` only where the README allows it.
- `save_issue` returns the whole issue. Call it once per ticket per turn with every change in that call; never to confirm a change or to touch the description.
- Notes and reasons go in `save_comment`, never a description edit.
- Change labels with `addLabels` and `removeLabels`; `labels` replaces the whole set.
- `list_issues` takes one `state` per call. Open tickets are three calls: `backlog`, `unstarted` (Todo), `started` (In Progress and In Review).
- Results are paged: while `hasNextPage` is true, pass the returned `cursor`.
- Relations come only from `get_issue` with `includeRelations: true`; put `relations` in `fields`.
- `updatedAt` on `list_issues` is a "changed since" filter (a timestamp).
- A status named `Duplicate` reads as Canceled; never move a ticket to it.

## Operations

### `list-tickets`

`list_issues` with `team: <TEAM>`, and any of `state`, `label`, `query` (words in the title), `parentId`, `updatedAt` (changed since), `limit` (up to 250), `fields` and `cursor`. Linear's `state` field is `status` (the filter argument is still `state`) and its `parent` is `parentId` (ask for it in `fields` to find epics). `relations` and `description` keep their names.

### `get-ticket`

`get_issue` with the identifier and `fields`. For relations pass `includeRelations: true` and `relations` in `fields`. Ask for `description` only where the README allows it.

### `read-comments`

`list_comments` with the issue identifier.

### `create-ticket`

`save_issue` without `id`, with `team: <TEAM>`, `state: Backlog`, `title`, `description` and, when set, `labels`, `priority` and `parentId`.

### `edit-description`

`save_issue` with `id` and `patch` for the one part that changes (read the description first).

### `set-state`

`save_issue` with `id` and `state` (Backlog, Todo, In Progress, In Review, Done or Canceled). Put any label change in the same call.

### `add-label`

`save_issue` with `id` and `addLabels`.

### `remove-label`

`save_issue` with `id` and `removeLabels`.

### `set-priority`

`save_issue` with `id` and `priority`: Urgent, High, Medium or Low.

### `comment`

`save_comment` with the issue identifier and `body`.

### `set-parent`

`save_issue` with `id` and `parentId`.

### `list-children`

`list_issues` with `parentId: <id>`; `limit: 1` when only existence matters.

### `set-blocked-by`

`save_issue` with `id` and `blockedBy`. Check the blocker's status first; never block on a Canceled or Duplicate ticket.

### `set-related`

`save_issue` with `id` and `relatedTo`.

### `ticket-url`

The issue's `url` field (add `url` to `fields`).

### `ensure-labels`

`list_issue_labels` for team `<TEAM>`, then `create_issue_label` for `agent` and `agent-skip` if either is missing.

## Setup

1. The Linear MCP is connected.
2. `project.md` § Identity has `Linear team name` and, if used, `Linear project`.
3. Run `ensure-labels` once.
