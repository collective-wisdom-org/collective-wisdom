# CW-38: Give each agent role its own GitHub user and persona

**Ticket:** [CW-38](https://github.com/dbeallor/collective-wisdom/issues/38)
**Status:** Shipped

## Goal

Every agent acts as the user's login today, so PRs, review comments and tickets all look like the user wrote them. After this ticket, each GitHub-facing role works as its own GitHub user with a short persona, and the trust rules that check logins accept the new users without trusting anyone else.

## Non-goals

- Non-GitHub trackers (Linear and Jira adapters stay as they are).
- Who may approve specs and merges. Only the user does.
- Merge rights for bot users. Merges keep running as the user's own login.
- Git commit authors. Commits keep the local `git config` name and email, and pushes keep the user's gh credential.
- The GitHub MCP server's token (`GITHUB_MCP_TOKEN`). Skills use `./scripts/gh.sh`.

## Today

- `agent-team/scripts/gh.sh` runs `gh` with `GITHUB_TOKEN` and `GH_TOKEN` unset, so every call uses the active account in the gh keyring: the user.
- `docs/agents/project.md` § Git and GitHub has one login row, `Owner login`. `agent-team/templates/project.md` has the same row.
- Code that compares logins:
  - `open-pr` § Team mode acts only on review comments from the owner login or a repo review bot.
  - `scripts/merge_pr.py` counts `## Code review`, `## Security review` and `Head moved to` comments only when their author is `gh api user` (the account running the script).
  - `scripts/cos_handoff.py` counts review comments the same way.
  - `scripts/cos_brief.py` `moved_line` counts a `Head moved to` note only from `gh api user`. The Chief of Staff runs this, but the child writes the note, so this breaks as soon as the two are different users.
  - The GitHub adapter (`trackers/github.md` § Conventions) counts `Approval withdrawn` only from the agent's own login, and treats a ticket author as trusted only with `triage`, `write`, `maintain` or `admin` on the repo.
- `org-chart.md` lists the roles. No personas exist.

## Design

### Which roles get a user

Four users. A role shares a user when it never writes to GitHub on its own or always runs inside another role's turn.

| User | Roles on it | Why |
|---|---|---|
| Chief of Staff | Chief of Staff, Project Manager pass, ticket helper | The pass runs inside the Chief of Staff's turn. The ticket helper is a one-shot the Chief of Staff starts, and its tickets are the Chief of Staff's requests. |
| Builder | Ship-loop child, implementer, documenter | The implementer and documenter never call GitHub. The child opens the PR, pushes notes and moves its ticket. |
| Code reviewer | Code review | Its PR comment is the point of the ticket. |
| Security reviewer | Security review | Same. |

The reviewers are read-only subagents, so the child still posts their comments, now as the reviewer's user (`AGENT_GH_ROLE=code-reviewer ./scripts/gh.sh pr comment ...`).

### Personas

New doc `agent-team/docs/agents/personas.md`, linked from `org-chart.md` and `docs/agents/README.md`. One short block per user:

| Persona | Suggested login | Role | Voice |
|---|---|---|---|
| Morgan | `cw-morgan` | Chief of Staff: runs the team, files and moves tickets | Brief and calm. Says what changed and what needs the user. |
| Sam | `cw-sam` | Builder: specs, builds and ships one ticket | Plain and concrete. Says what it did and what it left. |
| Riley | `cw-riley` | Code reviewer | Direct. Names the file and line, says why it matters. |
| Quinn | `cw-quinn` | Security reviewer | Careful. Names the risk, who could exploit it, and the fix. |

The doc also gives a one-line GitHub profile bio per persona. The logins are suggestions, since the accounts don't exist yet and a name may be taken. The real logins live in `project.md` (below), so an installed app can use other accounts or none. Voice is guidance for comment and PR prose within the `human-writing` rules. No signatures or headings change, because the scripts parse the comment headings.

### Logins in project.md

New rows in § Git and GitHub of `docs/agents/project.md` and `agent-team/templates/project.md`:

| Key | Value |
|---|---|
| Chief of Staff login | `none` until the account exists |
| Builder login | `none` |
| Code reviewer login | `none` |
| Security reviewer login | `none` |

`Owner login` stays the user. A `none` row means that role keeps using the active gh account, which is today's behavior. So an app that never sets the rows, or this repo before the accounts exist, works exactly as now.

`project_config.py` gets `role_login(role)` for the four role names `chief-of-staff`, `builder`, `code-reviewer`, `security-reviewer`, plus a tiny command line (`python3 -I scripts/project_config.py login <role>`) that prints the login or nothing, for `gh.sh`.

### Authentication

Each bot account is added to the user's gh keyring with `gh auth login`, next to the user's own account. gh keeps each account's token in the system keyring. Adding an account makes it active, so the setup ends with `gh auth switch -u <owner login>`.

`gh.sh` reads one environment variable, `AGENT_GH_ROLE`:

- Unset or empty: today's behavior, the active account.
- One of the four role names, with its `project.md` row unset: the active account.
- A role name with a login: `GH_TOKEN="$(gh auth token -u <login>)"` for that one `gh` process only, via `exec env -u GITHUB_TOKEN GH_TOKEN=... gh "$@"`. The token is never written to a file, never printed, and never exported beyond that process.
- An unknown role name, or a login the keyring doesn't have: exit 2 with one line on stderr (`gh.sh: no gh login for <login>; run gh auth login, then gh auth switch -u <owner>`) and no `gh` call. It doesn't fall back to the user, so a wrong setup can't quietly post as the user.

This keeps the `github-auth.md` rules: nothing exports `GITHUB_TOKEN`, no token is in the repo, and the user's own `gh` stays on the keyring account. The scripts in `scripts/` call `gh.sh`, so they inherit the role from their environment.

Callers set the role per command, because agent shells don't keep environment variables between commands:

- **Chief of Staff, Project Manager pass, ticket helper** (`chief-of-staff`, `project-manager`, `write-ticket` in team mode): every `./scripts/gh.sh` call and every script that calls it runs with `AGENT_GH_ROLE=chief-of-staff`.
- **Ship-loop child** (`ship-loop` § Team mode, `open-pr`, `merge-pr` team mode): every call runs with `AGENT_GH_ROLE=builder`, except the two below.
- **Review comments**: the child posts `## Code review (pass N)` with `AGENT_GH_ROLE=code-reviewer` and `## Security review (pass N)` with `AGENT_GH_ROLE=security-reviewer`.
- **Merge**: `scripts/merge_pr.py` runs with no role, so the merge and the branch delete stay on the user's login. Bots never merge.
- **Solo runs** and anything outside team mode: no role, so nothing changes for the user's own sessions.

`github-auth.md` gets a section "Agent users" with the setup steps: create the accounts, set each profile from `personas.md`, invite each as a collaborator, accept the invite, `gh auth login` each one, `gh auth switch` back, fill the `project.md` rows, then run the check (below).

### Trust rules

One rule everywhere: a team comment counts when its author is the login of the role that writes it, and when that row is `none`, the account running the check (today's rule).

- `merge_pr.py`: `## Code review` comments from the code reviewer login, `## Security review` from the security reviewer login, `Head moved to` from the builder login.
- `cos_handoff.py`: the same two review rules.
- `cos_brief.py` `moved_line`: the builder login. This fixes the case above where the Chief of Staff would never see the child's note.
- `open-pr` § Team mode: act on review comments from the owner login, the four team logins, or a repo review bot.
- GitHub adapter § Own login: the Chief of Staff login (or own login when unset) is the only author of `Approval withdrawn` that counts. The Chief of Staff is the only role that writes and reads it.
- GitHub adapter § Team tickets only: unchanged. Bot accounts are collaborators with write access, so tickets they file pass the existing check, and a user without triage or higher still fails it. The doc says so.

A comment by the owner login under a review heading doesn't count once the reviewer rows are set. A PR whose reviews were posted before the rows were filled has to run both reviews again.

### Check

`./scripts/gh.sh` with each role set runs `api user --jq .login` and must print that role's login. `github-auth.md` § Verify lists the four commands.

## Tests

- `test_project_config.py`: one table-driven test for `role_login` (set, `none`, missing row, unknown role).
- New `test_gh_sh.py`: one table-driven test that runs `gh.sh` with a fake `gh` first on `PATH` and a temp `PROJECT_MD`. Rows: no role (no `GH_TOKEN`, `GITHUB_TOKEN` removed), role with `none` row (same), role with a login (the fake `gh` sees `GH_TOKEN` from `auth token -u <login>`), unknown role and missing keyring login (exit 2, the fake `gh` never runs for the real command).
- `test_merge_pr.py` and `test_cos_handoff.py`: extend the existing tables with rows where the review or note author is the role login and where it is some other login. A comment by the running login must fail when a role login is set.
- `moved_line` in `cos_brief.py` has no test today. Add one small table (builder login counts, the running login doesn't once the row is set), since this is the case that breaks.

## Acceptance

- A PR opened by a child shows the builder user; its review comments show the code reviewer and security reviewer users. Checked live once the accounts exist (see Calls I made).
- A review comment or ticket from a team user is trusted; one from a user without write access is still data.
- No token is committed or exported as `GITHUB_TOKEN`.
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.

## Calls I made

- **You create the four GitHub accounts yourself.** Agents can't create accounts or accept invites. The PR ships the code, docs and personas with the `project.md` rows set to `none`, so nothing changes until you do the setup in `github-auth.md`. The live check (a PR and reviews showing the bot users) runs only after that. If the accounts exist before the build, the build fills the rows and runs it.
- **Bots get write access, so they can technically merge.** Collaborators on a personal repo always get write, and opening PRs needs it. Nothing in the team routes a merge through a bot: `merge_pr.py` runs as you. Blocking it at GitHub would need branch rules or an org, which is out of scope.
- **Four users, not seven.** The Project Manager pass and ticket helper share the Chief of Staff's user; the implementer and documenter share the builder's. All five children share one builder user.
- **The child posts the reviewers' comments** as the reviewer users. The reviewers stay read only, so the child holds all four tokens through the keyring.
- **A missing login fails, it doesn't fall back to you.** A wrong setup stops gh calls with a clear error instead of quietly posting as you.
- **Strict review authorship once set.** A `## Code review` comment counts only from the code reviewer user. In-flight PRs need their reviews re-run after the rows are filled.
- **Persona names and logins** (Morgan, Sam, Riley, Quinn; `cw-morgan` and so on) are suggestions. Change them in `personas.md` and `project.md` if a name is taken.
- **Commits and pushes stay yours.** Only gh calls (PRs, comments, tickets, labels) change user.
- **The role is an environment variable per command** (`AGENT_GH_ROLE=builder ./scripts/gh.sh ...`), not a flag or a lookup from the working directory, so scripts inherit it and nothing guesses.
- **The installed-app template gets the four rows** as `none`, so apps keep working without bot accounts.
