# CW-162: Choose the GitHub account per repo from the user install

**Status:** Shipped
**Shipped:** in PR #167, with differences: [as-built](../as-built/2026-11-07-cw-162-github-account-per-repo-as-built.md)
**Ticket:** [#162](https://github.com/collective-wisdom-org/collective-wisdom/issues/162)
**Follows:** CW-160 (install the team once per machine, merged in #164). Builds on its `~/.collective-wisdom` link and script call sites. CW-163 (`set up this repo`) writes the file this ticket defines.

## Goals

A person with more than one GitHub account has each repo use the right one. The login lives in a per-user file on the machine, not in a committed `project.md`, and the merge gate checks against it.

## Today

Facts from `main` at `bb44e3f` (CW-160 merged).

- `agent-team/scripts/gh.sh` is `exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"`, so every repo runs as the active keyring account. Every script reaches `gh` through it (`GH = <scripts dir>/gh.sh`).
- `merge_pr.read_facts` sets `owner` from `project_config.value("Owner login")`. `merge_pr.gate` stops with `project.md has no Owner login; ...` when it is unset, and with `gh is signed in as <login>, not the owner <owner>` unless the `gh api user` login is the owner or a `*` user in `.github/CODEOWNERS` (`merge_pr.codeowners`).
- `cos_approve_pr.approve` makes the same check, and raises `Cannot("read the Owner login from project.md")` when it is unset.
- `cos_untracked_check.trusted_logins` trusts the account running `gh` plus the `Owner login`.
- `agent_usage.py --ticket` reads `project_config.subscription_usage("Claude")`, the `Claude subscription API-equivalent usage` row, and shows the share of it only when it is a positive number.
- Both rows are in `docs/agents/project.md` (this repo) and `agent-team/templates/project.md`. Docs that name `Owner login`: `merge-pr/SKILL.md`, `chief-of-staff/SKILL.md` (untracked check), `docs/agents/github-auth.md`, `docs/agents/trackers/github.md` (whose `Approval withdrawn` counts). Test fixtures: `conftest.py`, `test_merge_pr.py`, `test_cos_approve_pr.py`, `test_cos_untracked_check.py`, `test_agent_usage.py`.
- Skills and docs call `~/.collective-wisdom/scripts/gh.sh`, which runs from the clone with the cwd in the app (`test_call_sites.py` enforces the path). `~/.collective-wisdom` is a link to `<clone>/agent-team`. `install.sh <app>` still copies `scripts/` into apps until CW-161 (#166, open) removes that route; either way `user_config.py` sits next to `gh.sh`, which finds it in its own folder.
- `cos_untracked_check.py` is the one script that passes `--repo`, with the `Repo` row of the root checkout's `project.md`.
- `gh auth token --hostname <host> --user <login>` prints one keyring account's token without changing the active account. `gh auth switch` changes it for the whole host.

## Design

### 1. `user.md`: where it lives and what it holds

One file per person per machine: `~/.config/collective-wisdom/user.md`. It is not under `~/.collective-wisdom`, because that is a link into the clone: a file there would sit in a git checkout, where it could be committed or lost when the clone is replaced.

It stores logins and one dollar figure, never tokens. The shape, kept in a new `agent-team/templates/user.md` that CW-163 copies when the file is missing:

```markdown
# collective-wisdom user settings

Settings for the agent team on this machine. It holds GitHub logins, never tokens.
`set up this repo` writes it. You can also edit it by hand.

## Settings

| Key | Value |
|---|---|
| Claude subscription API-equivalent usage (dollars) | `none` |

## GitHub accounts

One row per repo: the host and `owner/repo` of the repo's `origin` remote, and the gh login that acts there.

| Repo | Login |
|---|---|
| `github.com/collective-wisdom-org/collective-wisdom` | `example-login` |
```

Parsing follows `project.md`: the first backticked token in a cell is the value.

- The Settings row is read like `project_config.subscription_usage` today: a positive finite number, else none.
- A GitHub accounts row's Repo cell is `<host>/<owner>/<repo>`, compared case-insensitively. Its Login cell must be a GitHub login (letters, digits and single hyphens, at most 39 characters).
- Two rows for the same repo, or a malformed login in the row for this repo, is an error that names the file and line. The reader never picks one.
- A missing file, or a file with no row for this repo, means no mapped login. That is not an error.

### 2. `user_config.py`

New `agent-team/scripts/user_config.py`, the one reader of the file.

- `path()`: `Path.home() / ".config/collective-wisdom/user.md"`. Tests point `HOME` at a temp folder. No other override.
- `repo_key(root)`: reads `git -C <root> remote get-url origin` and returns `<host>/<owner>/<repo>` in lower case, or None. Accepted forms: `https://[user@]host[:port]/owner/repo[.git][/]`, `ssh://[user@]host[:port]/owner/repo[.git]` and `[user@]host:owner/repo[.git]`. The port is dropped. Anything else, or no `origin`, is None.
- `login(root)`: the mapped login for that repo, or None. Raises on the errors in § 1.
- `subscription_usage(provider)`: moved here from `project_config`, same rule, read from the Settings table.
- CLI for `gh.sh` and CW-163: `user_config.py account` prints `<host> <login>` for the cwd's git top level (`app_root.root()`), or nothing with exit 0 when there is no mapped login. On an error it prints `user_config: <reason>` to stderr and exits 2. `user_config.py path` prints the path.

### 3. `gh.sh` uses the mapped login for that command only

```
read the mapped account with user_config.py account (python3 -I)
exit 2 if that failed
no mapped account: exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"   (today's behavior)
mapped: token=$(env -u GITHUB_TOKEN -u GH_TOKEN gh auth token --hostname <host> --user <login>)
        on failure or an empty token: print "gh.sh: no gh login <login> on <host>; run gh auth login -h <host>" to stderr, exit 2, run nothing
        exec env -u GITHUB_TOKEN -u GH_TOKEN GH_TOKEN=<token> gh "$@"
```

- For a host other than `github.com` or `*.ghe.com`, the token goes in `GH_ENTERPRISE_TOKEN` instead, which is the variable gh reads for those hosts.
- The token exists only in the environment of that one `gh` process. It is never printed, logged or written.
- `gh.sh` never calls `gh auth switch`, so the active account and `gh auth status` stay as they were.
- The repo is the cwd's `origin`, not a `--repo` argument. Every script that passes `--repo` passes this repo's own `Repo` row, from the root checkout.
- A mapped login that is not in the keyring fails the command. It does not fall back to the active account, which could be the wrong person.

### 4. The merge gate and the trusted logins use the mapped login

- `merge_pr.read_facts`: `f["owner"] = user_config.login(ROOT)`. A `user_config` error is a failed read (the script's usual exit 2 path).
- `merge_pr.gate` with no owner: `user.md has no GitHub login for <repo key>; say set up this repo, or add the row by hand (github-auth.md § Account per repo)`. With a different login: `gh is signed in as <login>, not <owner>, the login user.md maps to <repo key>`. CODEOWNERS `*` users still pass, as today.
- `cos_approve_pr.approve`: the same lookup. No mapped login raises `Cannot("read this repo's GitHub login from user.md")`.
- `cos_untracked_check.trusted_logins`: the running account plus the mapped login, when there is one.
- No script reads `Owner login` after this, and there is no fallback to it.

### 5. Rows leave `project.md`

- Delete the `Owner login` and `Claude subscription API-equivalent usage` rows from `agent-team/templates/project.md` and this repo's `docs/agents/project.md`.
- `agent_usage.py --ticket` reads `user_config.subscription_usage("Claude")`. A missing file, row or figure leaves the cost line with no percentage, as an unset row does today. Delete `project_config.subscription_usage`.

### 6. Docs

- `docs/agents/github-auth.md`: new `## Account per repo` section: where `user.md` lives, its shape (link to the template), that `set up this repo` writes it, how to add a row by hand, what `gh.sh` does with it, and the verify step (`~/.collective-wisdom/scripts/gh.sh api user --jq .login` in each repo prints its login, and `gh auth status` shows the same active account). Replace every `Owner login` mention with the mapped login.
- `merge-pr/SKILL.md` gate list, `chief-of-staff/SKILL.md` untracked check and `trackers/github.md` (`Approval withdrawn` counts from the own login or the mapped login): `Owner login` becomes the login `user.md` maps to this repo.
- `README.md`: drop the `Claude subscription API-equivalent usage` bullet from `## Adopt in a repo` step 3 (it lists `project.md` rows), and add one line under `## Install on a machine` saying the per-machine settings (GitHub login per repo, subscription figure) live in `user.md`, with a link to `github-auth.md` § Account per repo.
- The `Layout` bullet for `agent-team/templates/` names `user.md`.

## Acceptance

From the ticket:

- A repo mapped to login A and a repo mapped to login B each call `gh.sh` and hit the matching account, and `gh auth status` shows the same active account as before the calls.
- A merge whose `gh` login is the mapped one passes the owner check. A login that is neither the mapped one nor a CODEOWNERS `*` user fails it.
- With no `Owner login` row, the gate does not fail with "project.md has no Owner login".
- Ticket cost shows a share of the subscription only when the install has a figure.

Added:

- `gh.sh` in a repo with no `user.md` row behaves exactly as today.
- A mapped login missing from the keyring stops `gh.sh` with exit 2 and runs no `gh` command.

## Testing

Table-driven, per `AGENTS.md` § Testing.

- `test_user_config.py`: one table for `repo_key` (https, https with user and `.git`, ssh scp form, `ssh://` with port, enterprise host, unknown form, no origin); one table for `login` and `subscription_usage` (match, case, no file, no row, two rows for the repo, bad login, figure set, figure `none`).
- `test_gh_sh.py`: a fake `gh` on `PATH` that records each call's args and token variables, a temp `HOME` and two temp repos with different `origin` remotes. Rows: repo A gets A's token, repo B gets B's, an unmapped repo gets no token, a missing keyring login exits 2 and makes no second call, and no call is ever `auth switch`. Keep the existing env-var test.
- `test_merge_pr.py`, `test_cos_approve_pr.py`, `test_cos_untracked_check.py`, `test_agent_usage.py`: switch the fixtures from the `Owner login` and subscription rows to a temp `user.md`. Update the gate rows for the two new messages; add none.
- `conftest.py`: drop `Owner login` from the fixture `project.md`.
- Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Non-goals

- Writing `user.md`, asking which account to store, and the first-run subscription question. `set up this repo` (CW-163) does that.
- `install.sh`. It neither creates nor reads `user.md`.
- `git fetch` and `git push`. They keep using git's own credentials, as today. Routing them through the mapped login is a later ticket if a second account needs it.
- A GitHub App identity (CW-112), and a committed list of extra people who may merge.
- Remotes other than `origin`, and `--repo` arguments that name another repo.

## Calls I made

- **Merges stop until `user.md` has a row for the repo.** There is no fallback to the old `Owner login` row. After this merges, this repo (and any app) needs its row before the next merge: `github.com/collective-wisdom-org/collective-wisdom` to the owner's login, plus the `12000` subscription figure, or ticket costs lose their percentage. The gate's message says how. I'll put the exact rows in the PR body's `After deploy`.
- **This ticket owns the `user.md` format.** CW-163's ticket puts the format out of its scope and only writes the row, and there is no CW-163 spec branch yet. CW-163 should create the file from `agent-team/templates/user.md` and use `user_config.py path`.
- **Merge order with CW-161.** CW-160 has merged, so nothing blocks the build. CW-161 (#166, open) edits many of the same files: `github-auth.md`, `merge-pr/SKILL.md`, `chief-of-staff/SKILL.md`, `templates/project.md`, this repo's `project.md` and `README.md`. Neither blocks the other; whichever merges second merges `main` in and resolves the conflicts. CW-161 leaves the `Owner login` row to this ticket. CW-163 builds after this one.
- **The file lives at `~/.config/collective-wisdom/user.md`,** outside the clone, so it can't be committed or lost with the clone. Not under `~/.collective-wisdom`, which is a link into the clone.
- **The repo key is the `origin` remote's host and `owner/repo`.** I did not resolve SSH host aliases: a remote like `git@work-gh:owner/repo` has host `work-gh`, which gh doesn't know, so that repo needs an https remote or the real host in its remote URL.
- **A mapped login missing from the keyring is a hard stop,** not a fall back to the active account. Acting as the wrong person is worse than a clear error.
- **No mapped login means today's behavior** for every `gh.sh` call, so unconfigured repos keep working. Only the merge gate and the approval check require the row.
- **One login per repo.** A duplicate row is an error, not "first wins".
- **The subscription figure is one value per machine,** in the same file, read from a `## Settings` table so later per-user settings have a home.
- **No env var override for the path.** Tests set `HOME`. A second way to point the gate at another file is one more thing to trust.

## Touches

Auth: the merge gate and the merge approval check now trust a machine-local file instead of a committed `project.md` row, and `gh.sh` hands a keyring token to each `gh` call. It also edits files on the approval path (`scripts/`, `docs/agents/`, `templates/project.md`, this repo's `docs/agents/project.md`). No data, money, user email or migrations.
