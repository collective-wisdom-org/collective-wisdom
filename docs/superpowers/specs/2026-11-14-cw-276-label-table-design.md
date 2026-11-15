# CW-276: Give ensure-labels the color and description of each team label

**Status:** Shipped
**Shipped:** in PR #363, as specified
**Ticket:** [#276](https://github.com/collective-wisdom-org/collective-wisdom/issues/276)
**Related:** #256

## Goal

A Chief of Staff that reads only `agent-team/docs/agents/trackers/github.md` can create every team label with the right color and description, without looking in another repo.

## Today

Facts from main at `81c114b`.

- `github.md` § `ensure-labels` shows `gh.sh label create <name> --color <hex> --description '<fixed text>'` and a one-line list of twelve names, plus "the area labels in `project.md`". It gives no `<hex>` and no `<fixed text>`, and no script holds them.
- In the CW-256 run the Chief of Staff searched skills, scripts and specs for about fifteen tool calls, then copied the values from `gh.sh label list --repo collective-wisdom-org/collective-wisdom`. That only works for someone who can read this repo, and the copy can drift.
- The live labels in `collective-wisdom-org/collective-wisdom` (read on 2026-11-14 with `gh.sh label list --json name,color,description`) match the ticket's list exactly:

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

- `status:backlog` is not a label: Backlog is the absence of a `status:` label.
- `linear.md` and `jira.md` § `ensure-labels` are not affected: Linear creates only `agent` and `agent-skip` through its own tool, and Jira needs none.

## Design

One file changes: `agent-team/docs/agents/trackers/github.md` § `ensure-labels`.

- The `Names:` line is replaced by the table above, so `<name>`, `<hex>` and `<fixed text>` in the `label create` line each come from one row. Colors are written without `#`, the form `gh label create --color` takes.
- One sentence under the table says Backlog has no label (no `status:` label means Backlog), so nobody adds a `status:backlog` row.
- Area labels from `project.md` keep their place after the table, created with `--description 'Area: <name>'` and no `--color`, so GitHub picks one. Area labels differ per app, so they get no fixed color.
- The step still creates only what is missing. A label that already exists with another color or description is left as it is.

No script, test or skill changes. The tracker doc test (`test_tracker_docs.py`) only checks the `### \`ensure-labels\`` heading, which stays.

## Leaves out

- Fixing the colors of labels that already exist with other values (no `label edit` step).
- A script or data file that holds the table; the doc is the one source.
- Linear and Jira adapters.
- `status:backlog`.

## Calls I made

- **Area labels get the description `Area: <name>` and no color.** The ticket covers only the twelve team labels; area labels need some description, and a fixed color would claim a meaning they don't have.
- **Existing labels are not updated.** `ensure-labels` stays create-only so re-running it never rewrites a label an app has restyled.
- **No new test.** No script parses the table, so per `AGENTS.md` § Testing a test would only restate the doc.
- **No plan.** The ticket changes one markdown file, so it builds from this spec (`kickoff-feature` step 6).
- **The ticket's 2026-11-13 comment says it was taken off the team's queue and left for Noah.** The Chief of Staff started this run afterwards, and the issue carries the `agent` and `status:in-progress` labels, so I treated the run as current. The older branch `feat/cw-276-ensure-labels-colors` is not used.
