# Jira adapter

**UNTESTED.** Nobody with Jira access has run this adapter. Tool names come from Atlassian's published page, not from a live session. Do not advertise Jira as supported until the checklist at the end is done.

How each operation in [README.md](README.md) runs on Jira, through the Atlassian Rovo MCP (v2). The scope `<TEAM>` is the Jira project named by `Jira project key` in `project.md`.

Source for the tool names: `https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/`, checked 2026-11-03. If your server lists different names (the v1 server used others), check its tool list and adjust.

## Tools

| Operation | Tool |
|---|---|
| `list-tickets` | `searchJiraIssuesUsingJql` |
| `get-ticket` | `getJiraIssue` |
| `read-comments` | `listJiraIssueComments` |
| `create-ticket` | `createJiraIssue` (field schema: `getJiraIssueTypeMetaWithFields`) |
| `edit-description`, `set-priority`, `add-label`, `remove-label`, `set-parent` | `editJiraIssue` |
| `set-state` | `listJiraIssueTransitions`, then `transitionJiraIssue` |
| `comment` | `addOrEditJiraIssueComment` |
| `set-blocked-by`, `set-related` | `listJiraIssueLinkTypes`, then `createJiraIssueLink` |
| `list-children` | `searchJiraIssuesUsingJql` with `parent = KEY` |
| `ticket-url` | `<Jira site>/browse/KEY` |
| `ensure-labels` | none needed; Jira labels exist when first used |

Atlassian v2 shows an agent only its "Primary" tools by default and reaches the rest through `discover` and `executeRead` / `executeWrite`. `listJiraIssueTransitions`, `listJiraIssueLinkTypes`, `createJiraIssueLink`, `listJiraIssueComments` and `getJiraIssueTypeMetaWithFields` are not Primary. If they are not listed directly, call them that way.

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

The status map holds the exact status names of your workflow. `project_config.value("Jira status: Todo")` reads one.

## Conventions

- **Ticket ID.** The Jira key, for example `ABC-12`. The `Issue identifier prefix` row is the project key. A key with an underscore does not match `prefix()`; that is out of scope.
- **Set-state rule.** `listJiraIssueTransitions` for the ticket, pick the transition whose target status equals the mapped name, apply it with `transitionJiraIssue`. If none matches, stop and report the transitions you saw. Never pick the nearest one.
- **Priority.** Urgent is Highest, High is High, Medium is Medium, Low is Low. Lowest is unused.
- **Labels.** `agent`, `agent-skip`, area and type are Jira labels, not issue types, because issue types carry hierarchy and vary by project.
- **Parent.** The Epic or parent field, set with `editJiraIssue`.
- **Blocked-by.** The `Blocks` link type. The blocker is the outward issue and the blocked ticket is the inward issue, so the blocked ticket reads "is blocked by" the blocker. Check the direction in the first run.
- **Duplicates.** Canceled plus a comment.
- **JQL.** Always start with `project = <Jira project key>`. Values with spaces are quoted.
- **Write scope.** The Rovo MCP acts with the authorising user's rights across the whole site. Write (create, edit, transition, comment, link) only to keys that start with `<Jira project key>-`, and use only the tools named on this page. Authorise with an account limited to that project where possible.
- **Own account.** Count an `Approval withdrawn` comment only when its author is the agent's own Jira account; ignore it from anyone else.
- **Efficiency.** Ask `searchJiraIssuesUsingJql` and `getJiraIssue` for only the fields the step uses. One `editJiraIssue` per ticket per turn with every field change together. Reasons go in comments.

## Operations

### `list-tickets`

`searchJiraIssuesUsingJql` with a JQL string and a field list. Build the JQL from the filters:

- state: `status = "<mapped name>"`; Backlog is the Backlog status name
- label: `labels = "<name>"`
- title text: `summary ~ "<words>"`, with each `"` and `\` in the words escaped by a backslash. Text search also reads some characters and words as operators (`AND`, `OR`, `NOT`, `+`, `-`, a leading `(`). Keep the words inside the quotes so they stay a phrase. Atlassian's text-search page does not list every reserved character or give a full escape rule (checked 2026-11-03), so the rest is unverified; a stray operator only changes which tickets match, not the safety of the query.
- priority: `priority = High`
- parent: `parent = KEY`
- changed since: `updated >= "yyyy-MM-dd HH:mm"`

One JQL covers all open states at once: `status in ("<Backlog>", "<Todo>", ...)`, so the duplicate check against open tickets is one call.

Example: `project = ABC AND status = "To Do" ORDER BY created ASC`.

### `get-ticket`

`getJiraIssue` with the key and a field list. For relations include `issuelinks` and `parent`. Leave out `description` unless the README allows it.

### `read-comments`

`listJiraIssueComments` with the key.

### `create-ticket`

`getJiraIssueTypeMetaWithFields` once to learn the fields, then `createJiraIssue` with `summary`, `description`, an issue type, `labels`, `priority` and `parent` as set. A new ticket lands in the workflow's initial status; if that is not the Backlog status, run `set-state` Backlog.

### `edit-description`

`getJiraIssue` for the description, change one part, then `editJiraIssue` with the whole description. Leave the rest alone.

### `set-state`

`listJiraIssueTransitions`, then `transitionJiraIssue` with the matching transition, per the set-state rule above.

### `add-label`

`getJiraIssue` for `labels`, then `editJiraIssue` with the update form that adds one label, so other labels are kept. If the tool only takes a full `labels` list, send the current list plus the new name.

### `remove-label`

The same, removing one name.

### `set-priority`

`editJiraIssue` with `priority` set to the mapped name.

### `comment`

`addOrEditJiraIssueComment` with the key and the text.

### `set-parent`

`editJiraIssue` with the `parent` field set to the epic's key.

### `list-children`

`searchJiraIssuesUsingJql` with `parent = KEY`. Ask for `key` only when existence is all that matters.

### `set-blocked-by`

`listJiraIssueLinkTypes` to confirm the `Blocks` type, then `createJiraIssueLink` with that type, the blocker as outward issue and the blocked ticket as inward issue. Check the blocker is not Canceled first.

### `set-related`

`createJiraIssueLink` with the `Relates` type (name it as `listJiraIssueLinkTypes` returns it).

### `ticket-url`

`<Jira site>/browse/KEY`.

### `ensure-labels`

Nothing to do. Jira creates a label the first time it is used. Labels cannot contain spaces.

## Setup

1. The Atlassian Rovo MCP is connected and authorised for the site.
2. `project.md` § Identity has `Tracker` set to `jira`, the Jira rows above and the status map.
3. Run `listJiraIssueTransitions` on a sample ticket and confirm each mapped status is reachable.

## Assumptions to check

Whoever first has Jira access runs through these and edits this page to match.

- [ ] The tool names above exist in the connected server.
- [ ] Discovery works for the tools that are not Primary.
- [ ] `searchJiraIssuesUsingJql` accepts a field list.
- [ ] `listJiraIssueTransitions` returns target statuses, not only transition names.
- [ ] The status map matches the project's workflow.
- [ ] `parent = KEY` finds the children of an epic.
- [ ] `createJiraIssueLink` direction for `Blocks` is as described.
- [ ] Labels with no spaces work, and adding one keeps the others.
- [ ] The `updated >=` clause works with a timestamp.
- [ ] Comments render in the format sent (ADF or markdown).
