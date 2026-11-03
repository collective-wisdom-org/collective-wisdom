# Linear adapter

How each operation in [README.md](README.md) runs on Linear, through the Linear MCP. This is the default tracker: a `project.md` with no `Tracker` row uses it.

The scope `<TEAM>` is the Linear team named in `project.md` § Identity (`Linear team name`). If `Linear project` is set, it narrows the scope.

## Rules

These are the Linear-only rules behind the shared efficiency rules in the README.

- `list_issues` and `get_issue` always pass `fields`, with only what the step uses. Ask for `description` only where the README allows it.
- `save_issue` returns the whole issue and can't be told to return less. Call it once per ticket per turn, with every change (state, labels, priority, parent) in that call. Never call it to confirm a change or to touch the description.
- Notes and reasons go in `save_comment`, never in a description edit.
- Change labels with `addLabels` and `removeLabels`. `labels` replaces the whole set and drops what it doesn't list.
- `list_issues` takes one `state` per call. Open tickets are three calls: `backlog`, `unstarted` (Todo), then `started` (In Progress and In Review).
- Results are paged. When `hasNextPage` is true, pass the returned `cursor` to get the next page.
- Relations come only from `get_issue` with `includeRelations: true`; ask for `relations` in `fields`.
- `updatedAt` on `list_issues` is a "changed since" filter: pass a timestamp.
- A Linear status name may be `Duplicate`. Treat it like Canceled when reading; never move a ticket to it.

## Operations

### `list-tickets`

`list_issues` with `team: <TEAM>`, and any of `state`, `label`, `query` (words in the title), `parentId`, `updatedAt` (changed since), `limit` (up to 250), `fields` (for example `[id, title, status, labels, priority, createdAt, updatedAt]`) and `cursor`. Linear's status field is named `status`; it holds the State.

### `get-ticket`

`get_issue` with the identifier and `fields`. For relations pass `includeRelations: true` and include `relations` in `fields`. Ask for `description` only where the README allows it.

### `read-comments`

`list_comments` with the issue identifier.

### `create-ticket`

`save_issue` without `id`, with `team: <TEAM>`, `state: Backlog`, `title`, `description` and, when set, `labels`, `priority` and `parentId`.

### `edit-description`

`save_issue` with `id` and `patch` for the part that changes. Read the description first, patch one part, and leave the rest alone.

### `set-state`

`save_issue` with `id` and `state` set to Backlog, Todo, In Progress, In Review, Done or Canceled. Put any label change in the same call.

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

`list_issues` with `parentId: <id>`. Pass `limit: 1` when only existence matters.

### `set-blocked-by`

`save_issue` with `id` and `blockedBy`. Check the blocker's status first; never block on a Canceled or Duplicate ticket.

### `set-related`

`save_issue` with `id` and `relatedTo`.

### `ticket-url`

The `url` field of the issue. Add `url` to `fields` when a step needs it.

### `ensure-labels`

`list_issue_labels` for team `<TEAM>`, then `create_issue_label` for `agent` and `agent-skip` if either is missing.

## Setup

1. The Linear MCP is connected to the Claude Code or Cursor session.
2. `project.md` § Identity has `Linear team name` and, if used, `Linear project`.
3. Run `ensure-labels` once.
