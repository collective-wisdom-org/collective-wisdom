# As-built: Ask setup questions before the Chief of Staff starts in a new repo

**Shipped:** in PR #168
**Ticket:** CW-163
**Spec:** [2026-11-06-cw-163-setup-questions-design.md](../specs/2026-11-06-cw-163-setup-questions-design.md)

## Differs from the spec

- The setup PR check (a remote `agent-team-setup` branch or open PR from it) runs when the status is read, before any question, not only at walk-through step 1, so `start the team` while the PR is open stops without asking again.
- `remove_app_copies.py` prints a TODO to commit the removal as a PR. The Chief of Staff passes on its `.claude/settings.json` line and drops the commit line, because the setup PR is that commit. The spec said to pass the TODO on as is.
- `setup_repo.py user` is skipped when this repo already has a mapped login and `user.md` exists; otherwise it runs after the last answer.
- The `ci` answer only takes `none` (written as `none (no CI yet)`); anything else leaves `TODO(<login>)`. Real check names are filled in by hand later.
- `write` takes `tracker_scope` for the Linear team name or Jira project key (alias `linear_team`), rejects unknown answer keys with exit 2, and on a fresh render needs `product`, `tracker`, `prefix`, `repo`, `test` and `approver` or `login`, and `tracker_scope` unless the tracker is `github`.
- `user` accepts the subscription as `none` or a positive plain decimal, and finds this repo's row anywhere in the file (like `user_config.login`), replacing the first and dropping duplicates.
- `status` keeps the repo name's case in `repo`; `repo_key` stays lower case.
- The `Linear team name` row holds the team name alone in backticks, so `project_config.setting` reads it.
- `agent-team/templates/project.md` is unchanged: the render fills its rows. The role doc and `SKILL.md` "never write code, edit branches or merge" lines name the setup walk-through as the one exception.
- `write` on an existing `project.md` that still holds template placeholders (status `placeholders`) fills the unset rows from the fresh render and keeps every value already set. It also inserts template rows the old file lacks, so an old file with no `Publish release notes` row (read as `on`) gets `off`. The diff is shown before anything is committed.
- A missing `Tracker` row reads as `linear`, as `project_config.tracker()` does, and `Tracker scope` is not required when `Linear team name` is set.
- A re-run that changes `tracker` fixes the rows that depend on it: github derives the scope from the repo, linear adds the Linear rows and needs `tracker_scope`, jira adds the Jira rows from `trackers/jira.md` as `TODO(<login>)`, and leaving linear or jira drops those rows.
- `rules` is written as a `Repo rules:` bullet under Repo invariants; a re-run replaces the `Repo rules:` bullet, else the `none yet` bullet, else the unfilled template bullet, else adds a bullet after the last one, and never touches other bullets.
- The walk-through step 1 offers to remove a leftover local branch, worktree or remote `agent-team-setup` branch with no open PR instead of stopping; step 7 also deletes the local branch. `git fetch origin` runs before `status` so `pinned` is current.
- Answers with `<` or `>` in `test`, `product`, `tracker_scope` or `linear_team` are rejected, because `status` would read them as placeholders.
- The worktree is `<tmp>/agent-team-setup-<name>`, with `<tmp>` from `mktemp -d`, and step 7 removes it with `rmdir`. The spec said `<tmpdir>/agent-team-setup-<repo>`.
- Step 6 passes `--title "docs: set up the agent team" --body-file <file>`.
- A no at step 2 or 3 removes the worktree and branch; a no at step 4 or later leaves them for the user.
- `status` adds `user_md_error` when `user.md` is malformed, and the skill tells the Chief of Staff to show it and stop.
