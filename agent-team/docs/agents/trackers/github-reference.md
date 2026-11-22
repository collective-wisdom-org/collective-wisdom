# GitHub Issues adapter reference

Read from `github.md`: `ensure-labels` and the setup labels table below, or to see what was not verified.

## ensure-labels table

List first, create only what is missing; safe to re-run. Create each missing label with `~/.collective-wisdom/scripts/gh.sh label create <name> --color <hex> --description '<fixed text>'` and the row's values.

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

A ticket with no `status:` label is in Backlog; there is no `status:backlog`. Area labels from `project.md` take `--description 'Area: <name>'` and no `--color`. An existing label is left as it is, whatever its color or description. Delete a label with `~/.collective-wisdom/scripts/gh.sh label delete <name> --yes`, which also strips it from issues.

## Unverified

- `label create` was run for `status:*`, `priority:urgent`, `priority:high` and `type:feature` only. The other names use the same command but were not created.
- The text fallbacks for `Blocked by:` and the sub-issue 404 path were not run, because the endpoints were on.
- Whether the sub-issue and dependency endpoints are on for other repos or plans.
- `set-related`: the `Related: #M` text line was written and read back; the both-tickets step was not separately run.
