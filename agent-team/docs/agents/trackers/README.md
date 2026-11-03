# Tracker operations

The agent team keeps its tickets in one tracker: Linear, GitHub Issues or Jira. Skills and role docs describe each ticket step as an operation from the table below and never name a tool. This page defines the operations. One adapter doc per tracker says how to do each one with that tracker's tools.

## Finding the adapter

Read the `Tracker` row in `docs/agents/project.md` § Identity. Its first backticked value is `linear`, `github` or `jira`. A missing row, an empty cell or `TODO(...)` text means `linear`. `python3 -c "import project_config; print(project_config.tracker())"` from `scripts/` prints the answer.

| Tracker | Adapter |
|---|---|
| `linear` | [linear.md](linear.md) |
| `github` | [github.md](github.md) |
| `jira` | [jira.md](jira.md) (untested) |

Load the adapter once per thread and reuse it. A skill that says "set-state In Review" means the `set-state` section of that adapter.

## Scope

`<TEAM>` in the skills stands for the scope of the tickets: the Linear team, the GitHub repo or the Jira project. `project.md` has the name or key.

## Operations

| Operation | Meaning |
|---|---|
| `list-tickets` | Tickets in the scope, filtered by state, label, priority, parent, text in the title or `updated since`, returning only the named fields |
| `get-ticket` | One ticket with the named fields, optionally with its relations (blockers, related, parent) |
| `read-comments` | The comments on a ticket |
| `create-ticket` | New ticket in Backlog with title, description, labels, priority, parent |
| `edit-description` | Patch part of a description without rewriting the rest |
| `set-state` | Move to Backlog, Todo, In Progress, In Review, Done or Canceled |
| `add-label`, `remove-label` | Change one label without touching the others |
| `set-priority` | Urgent, High, Medium, Low or none |
| `comment` | Post a comment |
| `set-parent` | Place the ticket under an epic |
| `list-children` | Tickets whose parent is a given ticket |
| `set-blocked-by` | Record that a ticket cannot ship until another does |
| `set-related` | Record that two tickets touch the same work |
| `ticket-url` | The link to put in a task, a PR body or a report |
| `ensure-labels` | One-time setup: create the labels the team needs if missing |

## Shared vocabulary

- **States:** Backlog, Todo, In Progress, In Review, Done, Canceled. Linear also has Duplicate. The other trackers treat a duplicate as Canceled with a comment.
- **Labels:** `agent` and `agent-skip` (Chief of Staff and the user only), one or two area labels, and one type label (`Feature`, `Improvement` or `Bug`).
- **Priority:** Urgent, High, Medium, Low, none.
- **Fields:** `id`, `title`, `state`, `labels`, `priority`, `createdAt`, `updatedAt`, `parent`, `relations`, `description`.

## Efficiency rules

These hold on every tracker.

- List calls ask for only the fields the step uses.
- Get calls leave out `description` unless the readiness check, the duplicate check or the Todo fill needs it.
- One write call per ticket per turn, carrying every change.
- Notes and reasons go in comments, never in a description edit.
- Never make a call just to confirm a change.

## Where the trackers differ

| Used by the Chief of Staff | Linear | GitHub | Jira |
|---|---|---|---|
| Labels `agent`, `agent-skip` | team labels | repo labels | Jira labels |
| Todo state | workflow state | `status:todo` label | status in the map |
| Scope | team | repo | project key |
| Blockers | issue relations | dependency API or `Blocked by:` line | `Blocks` link |
| Epic | parent issue | sub-issue API or `Parent:` line | Epic parent |

## Adding a tracker

Copy an existing adapter, keep the Setup section, and write one `### \`operation\`` section for every row of the operations table. `scripts/test_tracker_docs.py` fails if a section is missing. Add the tracker's tool names to the forbidden list in that test, and to the `Tracker` row's allowed values in `scripts/project_config.py`.
