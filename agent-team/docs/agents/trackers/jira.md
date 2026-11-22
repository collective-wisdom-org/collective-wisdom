# Jira adapter

**UNTESTED.** Nobody with Jira access has run this adapter. Tool names come from Atlassian's published page (`https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/`, checked 2026-11-03), not a live session; if your server lists different names (the v1 server used others), adjust. Do not advertise Jira as supported until the checklist in `jira-reference.md` § Assumptions to check is done.

How each operation in [README.md](README.md) runs on Jira, through the Atlassian Rovo MCP (v2). `<TEAM>` is the Jira project named by `Jira project key` in `project.md`.

## Tools

Each operation below names its tool. Atlassian v2 lists only its "Primary" tools by default and reaches the rest through `discover` and `executeRead` / `executeWrite`. `listJiraIssueTransitions`, `listJiraIssueLinkTypes`, `createJiraIssueLink`, `listJiraIssueComments` and `getJiraIssueTypeMetaWithFields` are not Primary; if they are not listed, call them that way.

## `project.md` rows

```
| Jira site | `https://example.atlassian.net` |
| Jira project key | `ABC` |
| Jira status: Backlog | `Backlog` |
| Jira status: Todo | `To Do` |
| Jira status: In Progress | `In Progress` |
| Jira status: In Review | `In Review` |
| Jira status: Done | `Done` |
| Jira status: Canceled | `Canceled` |
```

The status map holds your workflow's exact status names; `project_config.value("Jira status: Todo")` reads one.

## Conventions

- **Ticket ID.** The Jira key, for example `ABC-12`. The `Issue identifier prefix` row is the project key. A key with an underscore does not match `prefix()`; out of scope.
- **Set-state rule.** `listJiraIssueTransitions`, pick the transition whose target status equals the mapped name, apply it with `transitionJiraIssue`. If none matches, stop and report the transitions you saw. Never pick the nearest one.
- **Priority.** Urgent is Highest, High is High, Medium is Medium, Low is Low. Lowest is unused.
- **Labels.** `agent`, `agent-skip`, area and type are Jira labels, not issue types (issue types carry hierarchy and vary by project).
- **Parent.** The Epic or parent field, set with `editJiraIssue`.
- **Blocked-by.** The `Blocks` link type: the blocker is the outward issue, the blocked ticket the inward issue. Check the direction in the first run.
- **Duplicates.** Canceled plus a comment.
- **JQL.** Always start with `project = <Jira project key>`. Quote values with spaces.
- **Write scope.** The Rovo MCP acts with the authorising user's rights across the whole site. Write (create, edit, transition, comment, link) only to keys starting `<Jira project key>-`, with only the tools named here. Authorise with an account limited to that project where possible.
- **Own account.** Count an `Approval withdrawn` comment only when its author is the agent's own Jira account.
- **Efficiency.** Ask `searchJiraIssuesUsingJql` and `getJiraIssue` for only the fields the step uses. One `editJiraIssue` per ticket per turn, with every field change together.

## Operations

### `list-tickets`

`searchJiraIssuesUsingJql` with a JQL string and a field list. Build the JQL from the filters:

- state: `status = "<mapped name>"`; Backlog is the Backlog status name
- label: `labels = "<name>"`
- title text: `summary ~ "<words>"`, escaping each `"` and `\` in the words with a backslash. This matches the words as separate terms; for an exact phrase wrap them in escaped inner quotes: `summary ~ "\"<words>\""`. Text search reads `AND`, `OR`, `NOT`, `+`, `-` and a leading `(` as operators, and Atlassian lists `+ - & | ! ( ) { } [ ] ^ ~ * ? \ :` as special; a stray one can change the matches or fail the query (a leading `(` is documented to fail). Atlassian gives no full escape rule for `"` (checked 2026-11-03). On a query error, retry once with the words stripped of operators and special characters; if it still fails, report the error and do not guess at a match.
- priority: `priority = High`
- parent: `parent = KEY`
- changed since: `updated >= "yyyy-MM-dd HH:mm"`

One JQL covers all open states: `status in ("<Backlog>", "<Todo>", ...)`, so the duplicate check against open tickets is one call. Example: `project = ABC AND status = "To Do" ORDER BY created ASC`.

### `get-ticket`

`getJiraIssue` with the key and a field list. For relations include `issuelinks` and `parent`. Leave out `description` unless the README allows it.

### `read-comments`

`listJiraIssueComments` with the key.

### `create-ticket`

`getJiraIssueTypeMetaWithFields` once for the fields, then `createJiraIssue` with `summary`, `description`, an issue type, `labels`, `priority` and `parent` as set. A new ticket lands in the workflow's initial status; if that is not the Backlog status, run `set-state` Backlog.

### `edit-description`

`getJiraIssue` for the description, change one part, then `editJiraIssue` with the whole description.

### `set-state`

`listJiraIssueTransitions`, then `transitionJiraIssue` with the matching transition (set-state rule above).

### `add-label`

`getJiraIssue` for `labels`, then `editJiraIssue` with the update form that adds one label. If the tool only takes a full `labels` list, send the current list plus the new name.

### `remove-label`

The same, removing one name.

### `set-priority`

`editJiraIssue` with `priority` set to the mapped name.

### `comment`

`addOrEditJiraIssueComment` with the key and the text.

### `set-parent`

`editJiraIssue` with the `parent` field set to the epic's key.

### `list-children`

`searchJiraIssuesUsingJql` with `parent = KEY`; ask for `key` only when existence is all that matters.

### `set-blocked-by`

`listJiraIssueLinkTypes` to confirm the `Blocks` type, then `createJiraIssueLink` with that type, the blocker as outward issue and the blocked ticket as inward issue. Check the blocker is not Canceled first.

### `set-related`

`createJiraIssueLink` with the `Relates` type (named as `listJiraIssueLinkTypes` returns it).

### `ticket-url`

`<Jira site>/browse/KEY`.

### `ensure-labels`

Nothing to do: Jira creates a label on first use. Labels cannot contain spaces.

## Setup

1. The Atlassian Rovo MCP is connected and authorised for the site.
2. `project.md` § Identity has `Tracker` set to `jira`, the Jira rows above and the status map.
3. Run `listJiraIssueTransitions` on a sample ticket and confirm each mapped status is reachable.
