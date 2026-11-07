# CW-163: Ask setup questions before the Chief of Staff starts in a new repo

**Status:** Shipped
**Shipped:** in PR #168, with differences: [as-built](../as-built/2026-11-07-cw-163-setup-questions-as-built.md)
**Ticket:** [#163](https://github.com/collective-wisdom-org/collective-wisdom/issues/163)
**Follows:** CW-160 (machine install at `~/.collective-wisdom`, merged in #164), CW-161 (`install.sh` touches no app; `remove_app_copies.py`; PR #166 open), CW-162 (`user.md`, account per repo; spec only, on `feat/cw-162-github-account-per-repo` at `1994ac6`). The build starts after CW-161 and CW-162 merge, and follows what they merge.

## Goals

A person with the machine install opens a Chief of Staff thread in a repo that has never run the team, says `start the team` or `set up this repo`, and answers a few questions. The command writes `docs/agents/project.md` and the `.agent-team/` line in `.gitignore` on a branch, walks them through opening a PR for it, and teaches them how to run the Chief of Staff. Once the PR is merged, `start the team` works.

## Today

Facts from `main` at `bb44e3f`, CW-161's PR #166, and CW-162's spec at `1994ac6`.

- `start the team` follows `agent-team/.claude/skills/chief-of-staff/startup.md` § Setup: it checks the thread is on the root checkout and the merge target branch, then runs `cos_state.py init` and a full pass. Nothing creates `docs/agents/project.md` or asks for the prefix, tracker or test command.
- `agent-team/templates/project.md` holds `<...>` placeholders. `project_config.prefix()` stops rather than guess a missing prefix.
- On `main` (CW-160), `~/.collective-wisdom` links to the clone's `agent-team/`, and the user-level instruction (`agent-team/templates/machine-instruction.md`) says the team runs only in a repo with `docs/agents/project.md`.
- After CW-161 (PR #166), `install.sh <app>` exits 2 and writes nothing in an app, nothing seeds `project.md` or the `.gitignore` line (its PR leaves both to this ticket), and `~/.collective-wisdom/scripts/remove_app_copies.py [--dry-run] [--force]` removes an old app's copied team files and its pin (`docs/agents/installed-from.txt`). It exits 1 and lists hand-edited copies unless `--force`.
- After CW-162 (per its spec), `~/.config/collective-wisdom/user.md` holds a `## Settings` table with the `Claude subscription API-equivalent usage (dollars)` row and a `## GitHub accounts` table of `| Repo | Login |` rows keyed `<host>/<owner>/<repo>` in lower case. Its shape ships as `agent-team/templates/user.md`, with the subscription row set to `none`. `user_config.py` is its one reader (`path`, `repo_key`, `login`, CLI `account` and `path`). `gh.sh` uses the mapped login's token, and with no row it behaves as today. The `Owner login` and subscription rows leave `project.md`, and the merge gate needs the `user.md` row.

## Builds

### 1. Triggers

- New Chief of Staff command `set up this repo` (row in `chief-of-staff` SKILL.md § Commands and the skill description). It reads a new reference file, `agent-team/.claude/skills/chief-of-staff/setup.md`, which holds the whole flow below.
- `startup.md` § Setup gets a step 0: run `~/.collective-wisdom/scripts/setup_repo.py status`. On `missing` or `placeholders`, run setup.md and stop the turn. No `cos_state.py init`, no pass, no labels. On `set`, carry on as today.
- `machine-instruction.md` (CW-160) gains one exception: in a repo without `project.md`, `set up this repo` and `start the team` may still run, and only to do setup.

### 2. What counts as set up

`setup_repo.py status` reads the root checkout's `docs/agents/project.md`:

- `missing`: no file.
- `placeholders: <rows>`: any of `Tracker`, `Tracker scope`, `Issue identifier prefix`, `Repo`, `Test` is unset or still holds a template `<...>` placeholder. Linear also needs `Linear team name`.
- `set`: otherwise. `TODO(...)` in other rows (Lint, Typecheck) is allowed, as the template already says.

It also prints the facts the questions need, as JSON: `owner/repo` and host from `git remote get-url origin`, the merge target from `git ls-remote --symref origin HEAD` (falls back to `main`), the logins `gh auth status` lists for the host, this repo's mapped login (`user_config.login`) if any, whether `user.md` exists, whether `docs/agents/installed-from.txt` exists on the merge target, and a test command guess (below). It writes nothing.

### 3. The questions

Asked one at a time in the Chief of Staff thread, each with the guess in brackets so a bare reply takes it. Only what the script can't read:

1. **GitHub login**, only when `gh auth status` lists more than one account for the host and `user.md` has no row for this repo. One account is taken with no question. No account stops with: run `gh auth login`, then say `set up this repo` again.
2. **Subscription figure**, only when `user.md` does not exist yet (the first setup on this machine). A number or `none`; `none` is stored as `none`.
3. **Tracker**: `github`, `linear` or `jira`, default `github`. Linear asks the team name next; Jira asks the project key and leaves the extra Jira rows as `TODO(<login>)`.
4. **Issue prefix**, suggested from the repo name (first letters of its words, upper case, two to four letters). Must match `[A-Z][A-Z0-9]*`; anything else is asked again.
5. **Test command**, suggested from what the repo has: `package.json` with a `test` script gives `npm test` (or `pnpm test` / `yarn test` by lockfile), `pyproject.toml` or `pytest.ini` gives `pytest`, `go.mod` gives `go test ./...`, `Cargo.toml` gives `cargo test`. No guess means the user must type one.
6. **Repo rules** beyond the universal ones: local data directories never to delete and Docker rules. `skip` is fine.

Written with no question: `Repo` and the merge target from the remote, `Tracker scope` = `owner/repo` for `github`, approval tolerance `strict`, review mode `agents`, teammate approval `off`, release notes `off`, review after conflict `off`, Approver and every `TODO(<owner>)` set to the login, Product name = the repo name, `Required CI checks` = `none (no CI yet)` when the repo has no `.github/workflows/`, else `TODO(<login>)`. Template prose bullets with no answer (areas, product rules, security overlays, environments) become `none yet`. No `Owner login` row and no subscription row (CW-162).

### 4. Files written

- `setup_repo.py user --login <l> [--subscription <n|none>]` writes this repo's `## GitHub accounts` row (key from `user_config.repo_key` on the root checkout) in the file at `user_config.path()`. When the file is missing it first copies `agent-team/templates/user.md` without its example row, and sets the subscription value. It changes only those rows and creates `~/.config/collective-wisdom/` if needed. Not a git step, so no question. It runs before step 6 of § 5, so `gh.sh pr create` already runs as the mapped login.
- `setup_repo.py write --dir <worktree> --answers <json>` renders `templates/project.md` into `<dir>/docs/agents/project.md` (or, on a re-run, changes only the keys in the answers), and appends `.agent-team/` to `<dir>/.gitignore` when no line already ignores it. It writes nothing outside `--dir`, and refuses when `--dir` is not a worktree of the current repo or its branch is the merge target.

### 5. The PR walk-through

Every git and gh step is shown as the command it will run, and runs only after the user says yes. A no stops there and prints what is left to do by hand and where the files are. Nothing is ever pushed to the merge target.

1. `git fetch origin` and `git worktree add -b agent-team-setup <tmpdir>/agent-team-setup-<repo> origin/<target>`. The worktree sits outside the repo, so the root checkout stays on the merge target and gains no untracked files. An existing remote `agent-team-setup` branch or open PR from it stops here with its link: merge or close that first.
2. `setup_repo.py write` into the worktree, then `git -C <wt> diff` shown to the user.
3. If the merge target has `docs/agents/installed-from.txt`: offer `remove_app_copies.py --dry-run` in the worktree, show its list, then offer the real run. Exit 1 (hand-edited copies) shows the list and offers `--force` or skip. Its settings.json TODO is passed on as is.
4. `git -C <wt> add -A && git -C <wt> commit -m "docs: set up the agent team"`.
5. `git -C <wt> push -u origin agent-team-setup`. Before pushing, the flow checks the branch is not the merge target.
6. `~/.collective-wisdom/scripts/gh.sh pr create --base <target> --head agent-team-setup` with a body that lists the answers, the removed copies (if any) and the line "Merge this, pull the root checkout, then say `start the team`." The PR link goes in the reply.
7. `git worktree remove <wt>`.

The user merges the PR on GitHub. The team's merge gate is not used here: there is no ticket and no state yet.

### 6. Endings

- First setup on the machine (`user.md` did not exist, so question 2 was asked): end with the five lines from the ticket: talk to the chief in this thread from the root checkout on the merge target branch; merge the setup PR, pull, and say `start the team`; answer with `approve N` or `changes N: ...`; branch work happens in worktrees; `status` shows the board.
- Later repos: one line, merge the PR, pull, say `start the team`.
- `set up this repo` when `status` is `set`: show the current values (the asked ones, the defaults and this repo's `user.md` login), ask what to change, change only those keys, and run § 5 if any repo file changed. A `user.md`-only change needs no PR. No course. The pin offer (§ 5 step 3) still runs when there is a pin, even with nothing else to change.
- `start the team` while the setup PR is open (status still `missing` on the root checkout): say the PR is open, link it, and stop. It does not ask again.

## Non-goals

- The machine install, `user.md`'s path and format, `user_config.py`, `gh.sh` account selection, the merge-gate change (CW-160, CW-162).
- `remove_app_copies.py` itself (CW-161). This only offers to run it.
- Merging the setup PR, or fast-forwarding the root checkout for the user.
- Starting the team in the same turn as the questions.
- Lint, typecheck, areas and environments questions. They stay `TODO`/`none yet` for the user to edit later.
- Rewriting an app's `AGENTS.md` or `.claude/settings.json`.

## Acceptance

- In a git repo with no `docs/agents/project.md`, `start the team` asks the questions, writes `user.md`, and opens (with the user's yeses) a PR from `agent-team-setup` holding `docs/agents/project.md` and the `.gitignore` line. It prints the course and does not init Chief of Staff state. The root checkout is still on the merge target with no new files.
- The written `project.md` has real values for prefix, repo, tracker and test command, no `Owner login` row, and `setup_repo.py status` on it says `set`.
- A second repo on the same machine is not asked for the subscription figure and gets no course.
- `set up this repo` on a filled project shows the current values and changes only what the user names.
- An app with a pin is offered the removal, and the removed copies land in the same PR.
- Saying no to any git or gh step leaves nothing pushed. No step pushes to or commits on the merge target.

## Testing

One file, `agent-team/scripts/test_setup_repo.py`, table-driven:

- `status`: missing file, template as shipped, one required row unset, filled `github`, filled `linear` without team name.
- `write`: fresh render has no `<...>` in the required rows, no `Owner login` row, and reads back `set`; a re-run with one key changes only that row; the `.gitignore` line is added once (absent, present, present as `/.agent-team/`); refusal on a `--dir` that is not a worktree of the repo or is on the merge target.
- `user`: creates the file from the template (no example row) when missing, adds a row, keeps other repos' rows, replaces this repo's row, sets the subscription value only when the file was missing. `HOME` points at a temp folder, as in CW-162's tests.
- The test command guess, one row per marker file.

Questions and the walk-through are skill prose and are not tested. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Calls I made

- **Changes the ticket's scope: the command commits and opens a PR.** The ticket says "It does not commit" and "Nothing is committed". The user's new direction replaces both: setup writes `project.md` and the `.agent-team/` line on a branch and walks the user through commit, push and PR, asking before each git or gh step and never pushing to the merge target. It also offers `remove_app_copies.py` when the app still has the old copied files and a pin. The ticket's "tells the user to commit `project.md`" course line becomes "merge the setup PR, pull, and say `start the team`". Everything else in the ticket stays.
- **The setup branch lives in a temporary worktree outside the repo** (`<tmpdir>/agent-team-setup-<repo>`), not `.worktrees/`. The Chief of Staff thread must stay on the root checkout's merge target, and a new app doesn't ignore `.worktrees/` yet, so a worktree inside the repo would show up as untracked files.
- **Branch name `agent-team-setup`,** not the `feat/<prefix>-N-*` pattern: there is no ticket, and the prefix isn't set until this PR merges.
- **The user merges the setup PR by hand on GitHub.** The team's merge gate needs a ticket and state, which don't exist yet.
- **Only the `.agent-team/` line goes into `.gitignore`,** as the direction says, not the rest of `templates/gitignore` (`.worktrees/`, `.env` and so on).
- **`user.md` format is owned by CW-162.** This spec follows CW-162's spec at `1994ac6`: `~/.config/collective-wisdom/user.md`, created from `agent-team/templates/user.md`, read through `user_config.py`. CW-162 isn't built yet. If it merges something else, the build follows it and says so under "Differs from spec".
- **"First setup on this machine" means `user.md` does not exist.** CW-162's template ships the subscription row already set to `none`, so the row being there can't be the signal. The same signal decides both asking the figure and printing the course, so the two always go together. A user who deletes `user.md` gets the figure question and the course again.
- **The build waits for CW-161 and CW-162 to merge.** It calls `remove_app_copies.py` and `user_config.py`, and writes the file CW-162 defines. If either has not merged when the build starts, it stops with `BLOCKED:`.
- **Placeholders means the five rows the scripts need,** not any `<...>` in the file. A repo with real values and some `TODO` rows counts as set up.
- **Guesses for prefix and test command** are offered, and a bare reply takes them. The ticket says ask; a default makes the answer one word.
- **Defaults for rows the ticket doesn't list:** Approver and `TODO` owner are the login, Product name is the repo name, Required CI checks follows whether `.github/workflows/` exists.
- **A re-run leaves an old `Owner login` row alone** unless the user asks to change it; CW-162 owns removing it.
- **`machine-instruction.md` gets an exception** so the setup command can run in a repo that has no `project.md`. Without it, the CW-160 instruction would stop the Chief of Staff before it asks anything.
- **A script for the file writes, prose for the questions.** Rendering the template and the "set up or not" test have to be exact, so they are in `setup_repo.py` with tests. The conversation is in setup.md.

## Touches

none of: data, money, auth, user email, migrations. It writes `~/.config/collective-wisdom/user.md` (logins and the subscription figure, never tokens), and in the app only through a worktree branch and a PR the user approves step by step. The security review checks that `write` stays inside `--dir` and that nothing pushes to the merge target.
