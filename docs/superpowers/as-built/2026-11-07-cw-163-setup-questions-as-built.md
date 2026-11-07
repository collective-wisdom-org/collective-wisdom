# As-built: Ask setup questions before the Chief of Staff starts in a new repo

**Shipped:** in PR #168
**Ticket:** CW-163
**Spec:** [2026-11-06-cw-163-setup-questions-design.md](../specs/2026-11-06-cw-163-setup-questions-design.md)

## Differs from the spec

- The setup PR check (a remote `agent-team-setup` branch or open PR from it) runs when the status is read, before any question, not only at walk-through step 1, so `start the team` while the PR is open stops without asking again.
- `remove_app_copies.py` prints a TODO to commit the removal as a PR. The Chief of Staff passes on its `.claude/settings.json` line and drops the commit line, because the setup PR is that commit. The spec said to pass the TODO on as is.
- `setup_repo.py user` is skipped when this repo already has a mapped login and `user.md` exists; otherwise it runs after the last answer.
- The `ci` answer only takes `none` (written as `none (no CI yet)`); anything else leaves `TODO(<login>)`. Real check names are filled in by hand later.
- `write` takes `tracker_scope` for the Linear team name or Jira project key (alias `linear_team`), rejects unknown answer keys with exit 2, and on a fresh render needs `product`, `tracker`, `prefix`, `repo`, `test` and `approver` or `login`.
- `user` accepts the subscription as `none` or a positive plain decimal, and finds this repo's row anywhere in the file (like `user_config.login`), replacing the first and dropping duplicates.
- `status` keeps the repo name's case in `repo`; `repo_key` stays lower case.
- The `Linear team name` row holds the team name alone in backticks, so `project_config.setting` reads it.
- `agent-team/templates/project.md` is unchanged: the render fills its rows. The role doc and `SKILL.md` "never write code, edit branches or merge" lines name the setup walk-through as the one exception.
