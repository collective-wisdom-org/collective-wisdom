# Tracker choice: Linear, GitHub Issues or Jira

**Status:** Draft, awaiting approval
**Branch:** `feat/tracker-choice` (no ticket; this repo has no Linear project)
**Plan:** [2026-11-03-tracker-choice.md](../plans/2026-11-03-tracker-choice.md)

## Goal

Let an app pick the tool that holds its tickets: Linear (today's behaviour), GitHub Issues or Jira. The choice is one row in the app's `docs/agents/project.md`. Skills and the Chief of Staff stop naming Linear MCP tools and describe each step as a tracker-neutral operation ("move the ticket to In Review", "comment on the ticket"). One adapter doc per tracker says how to do each operation with that tracker's tools.

Success means:

- An app whose `project.md` has no `Tracker` row behaves exactly as it does now.
- An app that sets `Tracker` to `github` can run the whole loop with `./scripts/gh.sh` and no Linear MCP.
- An app that sets `Tracker` to `jira` has an adapter that follows Atlassian's published tool names. It is marked untested until someone with Jira runs it.

## Non-goals

- No change to any Chief of Staff gate or rule: the spec and merge approvals, lanes and caps, the `createdBy: "user"` checks, the stuck and rotation logic. Only tracker wording and tool names change.
- No Jira scripts. Jira is reached only through the Atlassian Rovo MCP, and no script in `agent-team/scripts/` talks to a tracker.
- No GitHub Projects v2. GitHub state lives in labels and open/closed, not in a project board.
- No migration tool that copies tickets between trackers.
- No tracker other than the three named.

## Design

### The `Tracker` row

`docs/agents/project.md` § Identity gets a row:

```
| Tracker (`linear`, `github` or `jira`) | `linear` |
```

The first backticked token in the Value cell is the tracker. A missing row, an empty cell or `TODO(...)` text means `linear`. `project_config.tracker()` returns `linear`, `github` or `jira`, and exits with a message on any other value. The template ships the row set to `linear`.

Tracker-specific rows sit next to it in Identity:

- Linear: the existing `Linear team name` and `Linear project` rows.
- GitHub: none beyond `Repo`, which is already in § Git and GitHub.
- Jira: `Jira site`, `Jira project key`, and a status map (below).

### Operation vocabulary

`agent-team/docs/agents/trackers/README.md` defines the operations. Skills use these names in prose and never name a tool.

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

The README also fixes the shared vocabulary:

- **Scope** is what `<TEAM>` means in the skills today: the Linear team, the GitHub repo, the Jira project. Skills keep writing `<TEAM>`; the README says what it stands for.
- **States**: Backlog, Todo, In Progress, In Review, Done, Canceled. Linear also has Duplicate; the other trackers treat a duplicate as Canceled with a comment.
- **Labels**: `agent` and `agent-skip` (Chief of Staff and the user only), one area label or two, one type label (`Feature`, `Improvement`, `Bug`).
- **Priority**: Urgent, High, Medium, Low, none.
- **Fields**: `id`, `title`, `state`, `labels`, `priority`, `createdAt`, `updatedAt`, `parent`, `relations`, `description`.
- **Efficiency rules** that hold on every tracker, lifted from chief-of-staff § Lean turns: list calls ask for only the fields the step uses; get calls leave out `description` unless the readiness check, the duplicate check or the Todo fill needs it; one write call per ticket per turn carrying every change; notes and reasons go in comments, never in a description edit; never write a call just to confirm a change.

### Adapter docs

`linear.md`, `github.md` and `jira.md` each have one section per operation, headed with the operation name in backticks, plus a Setup section. `linear.md` also absorbs the Linear-only rules that sit inline in chief-of-staff and project-manager now: pass `fields` on `list_issues` and `get_issue`, `save_issue` returns the whole issue so call it once per ticket per turn, `labels` replaces the set while `addLabels` and `removeLabels` do not, `state` takes one value per `list_issues` call (`backlog`, `unstarted`, `started`), `cursor` paging, `includeRelations`.

### Skill edits

Every skill, role doc, template and README line that names Linear or a Linear tool is reworded. Each skill that touches tickets gets one sentence: "Tracker operations are in `docs/agents/trackers/README.md`; the adapter is the one for the `Tracker` row in `docs/agents/project.md`." Tool lists such as "Linear: `list_issues`, `get_issue`, ..." become "Tracker: the operations in the adapter doc". Frontmatter descriptions say "tickets" or "the tracker" instead of Linear. The skill names do not change.

Where the Chief of Staff leans on a Linear-only feature, the adapter says how the tracker provides it:

| Used by CoS | Linear | GitHub | Jira |
|---|---|---|---|
| Labels `agent`, `agent-skip` | team labels | repo labels | Jira labels |
| Todo state | workflow state | `status:todo` label | status in the map |
| Team scope | team | repo | project key |
| Blockers | issue relations | dependency API or `Blocked by:` line | `Blocks` link |
| Epic | parent issue | sub-issue API or `Parent:` line | Epic parent |

### Scripts

`project_config.tracker()` is the only script change. No other script reads tracker state today (confirmed by search: `agent-team/scripts/` has no Linear reference).

### Docs test

`agent-team/scripts/test_tracker_docs.py` checks two things, so drift fails CI:

1. Each adapter doc has a heading for every operation named in `trackers/README.md`.
2. No file under `.claude/skills/`, `docs/agents/` (outside `trackers/`) or `templates/` names a tracker-specific tool (`save_issue`, `list_issues`, `get_issue`, `save_comment`, `list_comments`, `list_issue_labels`, `create_issue_label`, the Jira tool names, `mcp__linear`, `mcp__atlassian`).

## Per-tracker mapping

### Linear

Maps to the Linear MCP calls the skills use today, unchanged.

| Operation | Call |
|---|---|
| `list-tickets` | `list_issues` with `team`, `state`, `label`, `query`, `parentId`, `updatedAt`, `limit`, `fields`, `cursor` |
| `get-ticket` | `get_issue` with `fields`; `includeRelations: true` for relations |
| `read-comments` | `list_comments` |
| `create-ticket` | `save_issue` without `id`, `team`, `state: Backlog` |
| `edit-description` | `save_issue` with `id` and `patch` |
| `set-state` | `save_issue` with `state` |
| `add-label` / `remove-label` | `save_issue` with `addLabels` / `removeLabels` |
| `set-priority` | `save_issue` with `priority` |
| `comment` | `save_comment` |
| `set-parent` | `save_issue` with `parentId` |
| `list-children` | `list_issues` with `parentId`, `limit: 1` when only existence matters |
| `set-blocked-by` / `set-related` | `save_issue` with `blockedBy` / `relatedTo` |
| `ticket-url` | the issue `url` |
| `ensure-labels` | `list_issue_labels`, then `create_issue_label` |

### GitHub Issues

Every call goes through `./scripts/gh.sh`, never bare `gh`.

- **Ticket ID.** `<PREFIX>-N` where N is the issue number and the prefix is whatever `Issue identifier prefix` says (for example `GH`). Branch names, `ticket_re()` and the scripts need no change. Issue and PR numbers share one counter in a repo, so `GH-N` never matches a PR number.
- **States.** Labels `status:backlog`, `status:todo`, `status:in-progress`, `status:in-review`. An open issue with no `status:` label counts as Backlog. Closed as completed is Done; closed as not planned is Canceled. `set-state` swaps the `status:` label and closes or reopens in the same step.
- **Priority.** Labels `priority:urgent`, `priority:high`, `priority:medium`, `priority:low`. No `priority:` label is no priority.
- **Type and area.** Type labels are `type:feature`, `type:improvement`, `type:bug`, which avoids GitHub's default `bug` and `enhancement` labels. Area labels are used as written in `project.md`.
- **Parent and blocked-by.** Preferred: the GitHub sub-issue and issue-dependency REST endpoints through `./scripts/gh.sh api`. The adapter says how to detect support: a GET on the sub-issues endpoint for the repo returns 200 when the feature is on and 404 when it is not. Fallback: a first line in the body, `Parent: #N` or `Blocked by: #N`, which readers parse. The adapter picks the endpoint when the probe passes and records nothing in `project.md`; the probe runs once per session.
- **PR bodies** say `Closes #N`, so a merge closes the issue as completed. `merge-pr` still runs `set-state` Done, which is then a no-op apart from stripping the `status:` label.
- **Efficiency.** `./scripts/gh.sh issue list --json <fields> --limit N` for lists; one `issue edit` per ticket per turn with every `--add-label`, `--remove-label` and `--body` change together.
- **Setup.** `ensure-labels` is a documented list of `./scripts/gh.sh label create` commands that is safe to re-run: list the labels first, create only what is missing.

The adapter doc is checked against reality before this spec ships (plan task 9); the table above is the design intent, and the adapter doc records what actually worked.

### Jira

Via the Atlassian Rovo MCP (v2). Tool names below were taken from Atlassian's published supported-tools page on 2026-11-03, not from memory:

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

Three of the names differ from what the task brief recalled. The v2 page lists `listJiraIssueTransitions` (not `getTransitionsForJiraIssue`), `addOrEditJiraIssueComment` (not `addCommentToJiraIssue`) and `createJiraIssueLink` (not `createIssueLink`). The v1 names are not documented on the current page. The adapter uses the v2 names and tells an operator who sees v1 names to check the tool list.

Atlassian v2 shows only the "Primary" tools to an agent by default and reaches the rest through `discover` and `executeRead` / `executeWrite`. `listJiraIssueTransitions`, `listJiraIssueLinkTypes` and `createJiraIssueLink` are not Primary, so the adapter says to call them that way if they are not listed directly.

`project.md` rows for Jira:

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

`set-state` fetches the available transitions, picks the one whose target status equals the mapped name, and applies it. If none matches it stops and reports the transitions it saw; it never picks the nearest one. Priority maps Urgent to Highest, High to High, Medium to Medium, Low to Low. Labels (`agent`, `agent-skip`, area, type) are Jira labels, not issue types, because issue types carry hierarchy and vary by project. Parent is the Epic or parent field. Blocked-by is the `Blocks` link type, with the other ticket as inward issue.

**The whole Jira adapter is marked UNTESTED** at the top, with a checklist of the assumptions someone with Jira should run through (see Testing).

## Migration and backward compatibility

- Installed repos keep working with no edit. No `Tracker` row means `linear`, and the `linear.md` adapter maps every operation to the calls the skills make today.
- `install.sh` never overwrites `project.md`, so existing apps keep their rows. The new template row only reaches new installs. The README tells existing apps to add the row if they want to be explicit, or to switch.
- `install.sh` copies `docs/agents/` with `find`, so `trackers/` ships with no installer change. The plan checks this with a dry run.
- Switching an existing app from Linear to another tracker is not automated. In-flight tickets, `.agent-team/state.json` and the `agent` labels would not move. The README says to switch only with the team stopped and the state file empty.
- Skill wording changes are behaviour-neutral for Linear. The plan includes a diff review where every removed Linear tool reference has a matching adapter entry.

## Testing

- `project_config.tracker()`: unit tests for default (no row, empty cell, `TODO(...)`), each valid value, case, and a bad value exiting.
- `test_tracker_docs.py`: the two checks above. It runs in CI with the rest of `agent-team/scripts`.
- Linear: no live test. The adapter is a rewording of calls that already run; a reviewer compares the old and new text.
- GitHub: the plan has a live step against `dbeallor/collective-wisdom` on a throwaway issue. It runs every operation through `./scripts/gh.sh`, records what worked, fixes the adapter to match, then closes the issue and deletes the labels it created. An operation that cannot run for lack of auth is recorded as untested, not guessed.
- Jira: untested. `jira.md` opens with an UNTESTED banner and a checklist: the tool names exist in the connected server; discovery works for non-Primary tools; `searchJiraIssuesUsingJql` accepts a field list; `listJiraIssueTransitions` returns target statuses; the status map matches the workflow; `parent = KEY` finds children; `createJiraIssueLink` direction for `Blocks`; labels with no spaces work; the `updated >=` clause works with a timestamp; comment format (ADF or markdown) renders.
- CI: `python3 -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh`.

## Risks

- **Skill drift.** Neutral wording can hide a step that only worked because Linear did it for free (for example, Linear closes nothing by itself, GitHub does on `Closes #N`). Mitigation: the diff review in the plan, and the table of Linear-only features above.
- **GitHub label sprawl and races.** Two writers swapping `status:` labels can leave two on one issue. `set-state` removes every other `status:` label in the same edit, and readers treat the furthest-along label as the state if they find two.
- **Change check on GitHub.** The project manager's change check relies on an issue's updated time moving when only a label changes. The live test confirms it.
- **Sub-issue and dependency endpoints** may be off for a repo or plan. The text fallback covers it, and the probe tells which is in use.
- **Jira is unverified.** Workflow differences, field schemas and the v2 discovery layer can break the adapter in ways docs cannot show. The banner and checklist are the mitigation, and the Jira option should not be advertised as supported until someone completes the checklist.
- **Jira keys** may contain underscores, which `prefix()` rejects. Out of scope; the adapter notes it.
- **Larger skill text moved out of chief-of-staff** risks a gate being lost in the edit. Only tracker words change, and the plan's last task diffs each skill with the tracker words masked.

## Calls I made

- Operation IDs are kebab-case names in backticks (`set-state`), and the docs test keys on them.
- Added `edit-description`, `list-children`, `set-related` and `ensure-labels` to your list, because write-ticket, the ranking and the CoS setup use them.
- GitHub type labels are `type:feature`, `type:improvement`, `type:bug`, not GitHub's default `bug` and `enhancement`.
- GitHub: an open issue with no `status:` label is Backlog.
- Jira type and area are Jira labels, not issue types.
- Jira priority maps Urgent to Highest and leaves Lowest unused.
- Jira status rows are keyed `Jira status: <state>` so `project_config.value("Jira status: Todo")` reads them with no code change.
- `TODO(...)` or an empty Tracker cell reads as `linear`, matching the missing-row rule.
- Linear's Duplicate state has no equivalent elsewhere; duplicates become Canceled plus a comment.
- Jira tool names use Atlassian's v2 list. Three differ from the brief's recollection (see Jira section).
- Skills keep the `<TEAM>` placeholder; the tracker README defines it as the scope.
- The switch-tracker procedure is documented, not scripted.
- Spec and plan live in this repo's `agent-team/docs/superpowers/`, which the installer does not copy (it copies only the README).
