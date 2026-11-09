# CW-276: Give ensure-labels the color and description of each team label

**Status:** Draft
**Ticket:** [#276](https://github.com/collective-wisdom-org/collective-wisdom/issues/276)
**Related:** CW-256 (#256), the Cursor trial run that hit this gap.

## Goal

A Chief of Staff that reads only `agent-team/docs/agents/trackers/github.md` can create every team label without looking in another repo.

## Today

Facts from `main` at `304891f`.

- `github.md` § `ensure-labels` shows `gh.sh label create <name> --color <hex> --description '<fixed text>'` and a list of twelve names. It gives no value for `<hex>` or `<fixed text>`.
- No file under `agent-team/` holds the colors. A search for them finds nothing, so no script or test reads them either.
- In the CW-256 run the Chief of Staff spent about fifteen tool calls looking for the values, then copied them from `gh.sh label list --repo collective-wisdom-org/collective-wisdom`. That only works for someone who can read this repo.
- The live labels in `collective-wisdom-org/collective-wisdom`, read on 2026-11-09, match the values in the ticket for all twelve names.

## Builds

One change, in `agent-team/docs/agents/trackers/github.md` § `ensure-labels`. The `Names:` line is replaced with this table and these two notes:

| Name | Color | Description |
|---|---|---|
| `status:todo` | `ededed` | Team ticket state: Todo |
| `status:in-progress` | `fbca04` | Team ticket state: In Progress |
| `status:in-review` | `0e8a16` | Team ticket state: In Review |
| `priority:urgent` | `b60205` | Priority: Urgent |
| `priority:high` | `d93f0b` | Priority: High |
| `priority:medium` | `fbca04` | Priority: Medium |
| `priority:low` | `c2e0c6` | Priority: Low |
| `type:feature` | `1d76db` | Type: Feature |
| `type:improvement` | `5319e7` | Type: Improvement |
| `type:bug` | `d73a4a` | Type: Bug |
| `agent` | `0052cc` | Worked by the agent team |
| `agent-skip` | `cccccc` | Agent team skips this ticket |

- Pass the color without a leading `#`, and the description in single quotes as the command shows.
- Backlog has no label: it is the absence of a `status:` label.
- Also create the area labels in `project.md`, if it lists any. They differ per repo, so they are not in the table: choose a color and a short description. Nothing reads them.

The two commands above the table stay as they are, and so does "List first, create only what is missing."

## Leaves out

- `linear.md` and `jira.md`. Linear creates only `agent` and `agent-skip` with no color step, and Jira labels exist on first use.
- `chief-of-staff/startup.md` step 1, which says to create `agent` and `agent-skip` for every tracker. On GitHub the adapter creates all twelve, so the sentence undersells the step. It is outside this ticket; a Chief of Staff still reaches `github.md` from that step.
- A script that creates the labels.
- Changing the color of a label that already exists.
- The `## Unverified` note in `github.md` about which names `label create` was run for.

## Calls I made

- **No new test.** The change is prose in a doc and no script parses the table, so `AGENTS.md` § Testing says to skip it. The existing `test_tracker_docs.py` still runs against the file. Nothing checks the table against the live labels, so it can drift if someone recolors a label here.
- **Area labels get a sentence, not a value.** The ticket's acceptance says "every label", but area labels are per repo. The doc tells the Chief of Staff to choose, so it does not go looking.
- **Existing labels are left alone.** The step stays "create only what is missing", so a repo with a differently colored `agent` label keeps it.
- **Each row is written out** rather than the ticket's shorthand ("each described Priority: <Level>"), so the values can be copied straight into the command.
- **No plan.** The ticket changes only a markdown file, so the build runs from this spec.
