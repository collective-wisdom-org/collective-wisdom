# Set up a repo

Read this on `set up this repo`, or when startup.md § Setup step 0 says the repo is `missing` or has `placeholders`. It asks a few questions, writes `docs/agents/project.md` and the `.agent-team/` line in `.gitignore` on a branch, and walks the user through a PR. Then the turn ends. Do not run `cos_state.py init`, a pass, `ensure-labels` or the slot fill, and do not start a child.

The scripts are `python3 ~/.collective-wisdom/scripts/setup_repo.py` (below, `setup_repo.py`):

| Command | What it does |
|---|---|
| `status [--root DIR]` | Line 1 is `missing`, `set` or `placeholders: <rows>`. Line 2 is one line of JSON facts. Writes nothing. |
| `user --login L [--subscription N\|none]` | Writes this repo's row in `~/.config/collective-wisdom/user.md`. Creates the file from the template when it is missing; the subscription figure applies only then. |
| `write --dir WT --answers JSON\|@file` | Renders or updates `docs/agents/project.md` and the `.agent-team/` line in `.gitignore`, inside the worktree WT. Refuses a WT that is not a worktree of this repo, or is on the merge target. |

Run them from the root checkout. The facts in `status` line 2 are `host`, `repo`, `repo_key`, `target`, `gh_logins`, `mapped_login`, `user_md_exists`, `pinned`, `has_workflows`, `test_guess`, `prefix_guess` and `product_guess`. `user_md_error` is there only when `user.md` is malformed: show it to the user and stop.

The user's replies and the facts become the `--answers` JSON. Keys: `product`, `tracker` (`github`, `linear` or `jira`), `tracker_scope` (the Linear team name or Jira project key; derived for `github`), `prefix`, `repo` (`owner/repo`), `host`, `target`, `test`, `approver`, `login`, `ci` (`none` when the repo has no CI, else leave it out) and `rules` (a list of strings). Put nothing with a backtick, a `|` or a newline in a value; ask again for a shorter, plainer answer. Free-text values (`product`, `tracker_scope`, `test`) take no `<` or `>` either. Always pass `login`. Pass the JSON as a file (`@file`) so the shell does not have to quote it.

## Check the status

Run `git fetch origin` first, so `pinned` is current.

1. Run `setup_repo.py status` and keep its facts.
2. Preconditions: this thread runs at the root checkout, on the merge target branch (`target`). If not, stop and tell the user.
3. The status decides what happens:

| Status | Do |
|---|---|
| `missing` or `placeholders: <rows>` | Check for an open setup PR first (§ The PR walk-through step 1); if there is one, stop there and don't ask the questions. Otherwise ask them. |
| `set` | Follow § Set up again. |

## The questions

Ask one at a time, in this thread. A bare reply takes the guess.

Status `placeholders`: ask only the questions whose rows `status` lists (`Tracker`, `Tracker scope`, `Linear team name` is question 3; `Issue identifier prefix` is 4; `Test` is 5; `Repo` has none, it comes from the remote). Use the file's current value as the guess where it has one, and pass only the answers for those rows. `write` applies an answer only to an unset row; every row the file already sets keeps its value.

| # | Question | Ask when | Guess |
|---|---|---|---|
| 1 | Which GitHub login for this repo? | `gh_logins` has more than one login and `mapped_login` is empty (`user.md` has no row for this repo) | the first of `gh_logins` |
| 2 | How many dollars of Claude subscription usage (API equivalent) do you want counted? A number or `none`. | `user_md_exists` is false | `none` |
| 3 | Which tracker: `github`, `linear` or `jira`? | always | `github` |
| 4 | What issue prefix? | always | `prefix_guess` |
| 5 | What command runs the tests? | always | `test_guess` |
| 6 | Any repo rules, such as local data directories that must never be deleted, or Docker rules? `skip` is fine. | always | `skip` |

Rules for each:

1. **GitHub login.** One login in `gh_logins` is taken unasked, as is `mapped_login`. No login stops the setup with: run `gh auth login`, then say `set up this repo` again.
2. **Subscription figure.** Goes to `setup_repo.py user --subscription`.
3. **Tracker.** Linear asks one follow-up, the team name. Jira asks one follow-up, the project key (`tracker_scope`); `write` adds the Jira rows listed in trackers/jira.md § project.md rows as `TODO(<login>)`. For `github` nothing more is asked: the scope is `owner/repo`.
4. **Issue prefix.** It must match `[A-Z][A-Z0-9]*`. Anything else, ask again.
5. **Test command.** With no `test_guess`, the user must type one.
6. **Repo rules.** One plain sentence each, into `rules`.

Written with no question:

| Row | Value |
|---|---|
| Repo, merge target | `repo`, `host` and `target` from the facts |
| Tracker scope | `owner/repo` for `github` |
| Approval risk tolerance | `strict` |
| Review mode | `agents` |
| Require teammate approval | `off` |
| Publish release notes | `off` |
| Review after conflict resolution | `off` |
| Approver, and every `TODO(<owner>)` | the login |
| Product name | `product_guess` (the repo name) |
| Required CI checks | `none (no CI yet)` when `has_workflows` is false, else `TODO(<login>)` |
| Template prose bullets with no answer (areas, product rules, security overlays, environments) | `none yet` |

There is no `Owner login` row and no subscription row in `project.md`; both live in `user.md`.

When all the answers are in, run `setup_repo.py user --login <login>`, adding `--subscription <n|none>` when question 2 was asked. It needs no yes. It runs before the PR steps so `gh.sh pr create` runs as the mapped login. Skip it with a `mapped_login` and nothing else to record.

## The PR walk-through

Show each git and gh step as the command it will run, and run it only after a yes. A no stops there: print what is left to do by hand and where the files are, and end the turn. A no at step 2 or 3 first removes the worktree and then the branch (`git worktree remove <wt>`, then `git branch -D agent-team-setup`; nothing is committed). A no at step 4 or later leaves `<wt>` and the branch for the user: say where `<wt>` is and which commands finish the job. Never push to the merge target, and never commit on it.

`<target>` is the merge target branch, `<name>` is `product_guess` (the part of `repo` after the slash). `<wt>` is `<tmp>/agent-team-setup-<name>`, with `<tmp>` from `mktemp -d`, outside the repo, so the root checkout stays on the merge target with no untracked files.

1. **Branch and worktree.** Look for leftovers of an earlier run:
   - An open PR from `agent-team-setup` (`~/.collective-wisdom/scripts/gh.sh pr list --head agent-team-setup --state open`): say it is open, give the link, and stop.
   - A remote branch with no open PR (`git ls-remote --heads origin agent-team-setup`): offer `git push origin --delete agent-team-setup`, and run it after a yes. It is not the merge target.
   - A local branch (`git branch --list agent-team-setup`) or a worktree on it (`git worktree list`): offer `git worktree remove --force <path>`, then `git branch -D agent-team-setup`, and run them after a yes.

   On a no to an offer, stop. With nothing left over:
   ```
   git fetch origin
   git worktree add -b agent-team-setup <wt> origin/<target>
   ```
2. **Write the files.** Run `setup_repo.py write --dir <wt> --answers @<file>`, then show `git -C <wt> diff` (and `git -C <wt> status --short` for the new files).
3. **The pin offer.** Only when `pinned` is true. Run `python3 ~/.collective-wisdom/scripts/remove_app_copies.py --dry-run` with `<wt>` as the current directory, show its list, and offer the real run. On exit 1 (hand-edited copies) show the list and offer `--force` or skip. Pass its `.claude/settings.json` TODO on to the user as it is. Drop its "commit this removal as a PR" line: this PR is that.
4. **Commit.**
   ```
   git -C <wt> add -A && git -C <wt> commit -m "docs: set up the agent team"
   ```
5. **Push.** First check the branch is `agent-team-setup`, not `<target>`. Then:
   ```
   git -C <wt> push -u origin agent-team-setup
   ```
6. **Open the PR.**
   ```
   ~/.collective-wisdom/scripts/gh.sh pr create --base <target> --head agent-team-setup --title "docs: set up the agent team" --body-file <file>
   ```
   The body, written to `<file>` first, lists the answers, the removed copies (if any) and: "Merge this, pull the root checkout, then say `start the team`." Put the PR link in the reply.
7. **Clean up.** `git worktree remove <wt>`, then `git branch -D agent-team-setup` (only after the worktree is gone), then `rmdir <tmp>`.

The user merges the PR. No merge gate applies: there is no ticket or state yet. Do not merge it or pull the root checkout for them.

## Endings

End the turn with one of these. After a no, print the hand-over from § The PR walk-through instead.

| Case | Say |
|---|---|
| First setup on this machine (`user_md_exists` was false, so question 2 was asked) | The five lines below. |
| A later repo | One line: merge the PR, pull the root checkout, then say `start the team`. |

The five lines for a first setup:

1. Talk to the chief in this thread, from the root checkout on the merge target branch.
2. Merge the setup PR, pull, and say `start the team`.
3. Answer with `approve N` or `changes N: ...`.
4. Branch work happens in worktrees, never in the root checkout.
5. `status` shows the board.

## Set up again

`set up this repo` when the status is `set`:

1. Show the current values from `docs/agents/project.md` (tracker, scope, prefix, test command, rules, the defaults) and this repo's login (`mapped_login`).
2. Ask what to change. Build `--answers` from the changed keys alone: on a re-run `write` changes only the rows for the keys it is given. A new `tracker` also fixes what hangs on it: `github` takes the scope from `repo`; `linear` needs `tracker_scope` (the team name) and adds the Linear rows; `jira` adds the Jira rows; leaving linear or jira drops its rows. `rules` replaces the `Repo rules: ` bullet, else the `none yet` bullet, else the template placeholder bullet, else adds a bullet; a bullet you wrote stays. A file that still holds template placeholders in a required row gets them filled like a first setup would, from the answers given and the values it already has; it gets no `Publish release notes` row if it lacks one. An old `Owner login` row is left alone unless the user asks to change it.
3. If a repo file changed, run § The PR walk-through from step 1. A change to `user.md` alone (a new login) goes through `setup_repo.py user` and needs no PR.
4. The pin offer (step 3) still runs when `pinned` is true, even with nothing else to change; then the PR holds just the removed copies.
5. No course at the end. Say what changed, and for a PR, to merge it and pull.
