# CW-112: One GitHub App as the agent team's identity

**Ticket:** [CW-112](https://github.com/collective-wisdom-org/collective-wisdom/issues/112)
**Status:** Proposed

## Goals

- When a repo sets up a GitHub App in `project.md`, the team's PRs, branch commits, pushes, review comments and ticket edits carry the app's bot identity, not the owner's login.
- The owner's own login still runs the merge (`merge_pr.py`) and the merge approval check (`cos_approve_pr.py`).
- With the app rows set to `none`, every script and skill behaves as today. That is the default for installed apps and for this repo until the owner registers the app.
- No private key or token is written to the repo, git config, the remote URL or any file.

## Non-goals

- Registering the app. That needs the owner in GitHub's web UI; `github-auth.md` gives the steps.
- One app per role, formal changes-requested reviews (#91), changing the merge gate, deleting the four old user accounts.
- The GitHub MCP server's token. It stays as `github-auth.md` describes.

## Today

Facts from `main` at `59c9b12`, checked 2026-11-05.

- `agent-team/scripts/gh.sh` is one line: `exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"`. Commits and pushes use plain git with the machine's config and credential (CW-110 deleted `scripts/git.sh`).
- `cos_brief.own_login()` runs `gh.sh api user -q .login`. `cos_brief.py` (`moved_line`) and `cos_handoff.py` count review comments and the `Head moved to` note from that login.
- `merge_pr.py` `read_facts` reads one `login` from `gh.sh api user`. `gate` requires it to equal `Owner login`, and `review` and `stands` count comments from the same login. So today the reviewer and the merger must be the same account.
- `cos_approve_pr.py` `read_gh` reads the login the same way and stops unless it is `Owner login`.
- `trackers/github.md` § Conventions trusts an issue only if its author has triage or higher on the repo (collaborator permission endpoint), and names the "own login" as `gh.sh api user`.
- `project_config.value()` reads the first backticked token of a row; `none` reads as unset.

## Design

### Config

Two new rows in § Git and GitHub of `agent-team/templates/project.md` and this repo's `docs/agents/project.md`, both `none`:

| Key | Value |
|---|---|
| GitHub App slug (agent identity; `none` = the account running `gh`) | `none` |
| GitHub App id | `none` |

The app counts as configured only when both rows have a value; one set without the other is an error the helper reports (exit 2), not a silent fallback. The installation id is not a row: the helper looks it up from the repo (`GET /repos/<owner>/<repo>/installation`).

The private key never goes in `project.md`. The helper reads it from `$AGENT_GH_APP_KEY` if set, else `~/.config/agent-team/<slug>.pem`. It refuses a key path inside the repo's working tree and a key file readable by group or others (mode must be `0600` or `0400`).

### Token helper: `agent-team/scripts/gh_app.py`

Python, stdlib only. Signs the JWT with the `openssl` CLI (`openssl dgst -sha256 -sign <key>`), which macOS and Linux ship; no new Python dependency.

- `gh_app.py token`: build the JWT (`iat` now minus 60s, `exp` now plus 9 minutes, `iss` = app id), look up the installation, `POST /app/installations/<id>/access_tokens`, print the token on stdout and nothing else. Errors go to stderr as `gh_app: <reason>` with exit 2. The reasons it names: no key file, key file mode too open, key inside the repo, openssl failed, app id rejected (401), JWT expired or clock skew (401 with GitHub's "expired" message), app not installed on the repo (404), any other HTTP error.
- `gh_app.py login`: print `<slug>[bot]`.
- `gh_app.py email`: print `<bot-user-id>+<slug>[bot]@users.noreply.github.com`, with the id from `GET /users/<slug>[bot]`.
- The API base is `https://api.github.com`, passed as a function argument the tests replace with a local fake server. It is not read from env or the command line, so nothing outside the tests can send the JWT elsewhere.
- No cache. Each call mints a fresh token (two API calls; installation tokens live an hour and the app's limit is far above the team's use). Nothing is written to disk.

### `gh.sh`

- App not configured, or `AGENT_GH_AS=owner` in the environment: today's line, unchanged.
- App configured: `GH_TOKEN="$(python3 gh_app.py token)"`, then `exec env -u GITHUB_TOKEN gh "$@"` with that `GH_TOKEN`. If the helper fails, `gh.sh` prints its reason and exits 2. It never falls back to the owner's login, so a broken setup can't quietly put team actions under the owner's name.

### `git.sh` (new, `agent-team/scripts/git.sh`)

Children commit and push through it. App not configured: `exec git "$@"`, exactly as plain git today.

App configured:

- `git.sh commit ...`: runs `git -c user.name='<slug>[bot]' -c user.email='<email>' commit ...`, so author and committer are the bot and GitHub links the commit to the app.
- `git.sh push ...`: mints a token, puts it in an environment variable, and runs `git -c credential.helper= push ...` with `GIT_ASKPASS` pointing at a small script in `agent-team/scripts/` that answers `x-access-token` for the username prompt and the variable for the password. The token never appears in argv, `git config`, `.git/config` or the remote URL, and the existing credential helper is skipped for that one command so it doesn't store the token.
- Any other subcommand: plain `git`.

### Whose comments count

New `cos_brief.team_login()` replaces `own_login()`: `<slug>[bot]` when the app is configured, else `gh.sh api user` as today. A matcher `same_login(a, b)` treats `<slug>`, `<slug>[bot]` and `app/<slug>` as one login, because `gh`'s JSON shows bot authors in different forms depending on the field (see Calls I made).

- `cos_brief.py` and `cos_handoff.py` use `team_login()` and `same_login()`.
- `merge_pr.py` `read_facts` keeps `login` (from `gh.sh api user` under `AGENT_GH_AS=owner`) for the owner gate and adds `team` from `team_login()`. `review` and `stands` count comments by `team`. With the app not configured `team` equals `login`, so behaviour is unchanged.
- `merge_pr.py` and `cos_approve_pr.py` set `AGENT_GH_AS=owner` in their own process before any `gh.sh` call. Every `gh.sh` call they make (merge, ticket move, release-notes publish, PR reads) runs as the owner, as today.

### Tracker trust

`trackers/github.md` § Conventions: an issue or comment by the app's bot login counts as the team's own and is trusted (the collaborator endpoint doesn't list app bots, so the permission check would wrongly drop tickets the team files). Only that exact bot login is added; every other author still goes through the permission check. "Own login" becomes the app's bot login when configured.

### Docs and skills

- `github-auth.md`: new § GitHub App. Register the app under the org (no webhook; repository permissions Contents, Pull requests and Issues read and write, Metadata, Checks and Commit statuses read), install it on the repo, save the key to `~/.config/agent-team/<slug>.pem` with mode 0600, fill the two rows. Which calls need the owner: `gh.sh api user` fails under the app token, so anything needing the owner's identity sets `AGENT_GH_AS=owner` (`merge_pr.py` and `cos_approve_pr.py` do it themselves). § Verify gains the app checks: `./scripts/gh.sh api user` fails (an installation token has no user), `./scripts/gh.sh api repos/<owner>/<repo>` succeeds, `python3 scripts/gh_app.py login` prints the bot login, and `git config --list` and the remote URL show no token after a push.
- `ship-loop` § Team mode (GitHub account), `open-pr`, `merge-pr`, `security-review`, `chief-of-staff`, `build-from-plan` (who commits), `org-chart.md` line 105: say the team acts as the app's bot when one is configured and as the account running `gh` otherwise; commit and push with `./scripts/git.sh`; merges and merge approval checks stay on the owner's login.

### Tests

Following `AGENTS.md` § Testing, one table-driven test per rule:

- `test_gh_app.py`: token helper error paths against a local `http.server` fake: missing key, key mode too open, key in the repo, bad app id (401), expired JWT (401), not installed (404), and the happy path printing only the token. Uses a throwaway RSA key generated with `openssl genrsa` in `tmp_path`.
- `test_gh_sh.py`: one table over (no app, app configured, app configured plus `AGENT_GH_AS=owner`, helper fails) checking which `GH_TOKEN` the fake `gh` sees and the exit code.
- `test_git_sh.py`: fake `git` on PATH; with the app configured, `commit` gets the bot name and email and `push` gets `credential.helper=` and `GIT_ASKPASS` with no token in argv; with no app, args pass through unchanged.
- `test_merge_pr.py`: extend the existing review table with rows where the reviewer is the bot and the merger is the owner (counts), and where a comment comes from another login (doesn't).

## Acceptance

- With both app rows `none`: the full suite passes unchanged and `gh.sh`, `git.sh`, `merge_pr.py`, `cos_brief.py` and `cos_handoff.py` behave as today.
- With the app configured (proved once the owner registers it): a ship-loop PR's author, every branch commit and both review comments show the bot; `./scripts/gh.sh api user` fails; `merge_pr.py` merges as the owner and `cos_approve_pr.py` still requires the owner's keyring login.
- No key or token in the repo, `git config --list`, `.git/config` or the remote URL after a push.
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.

## Calls I made

- **This PR ships with the app rows set to `none`.** Registering the app needs the owner in GitHub's web UI, so the first PR with the bot as author comes after you register it, save the key and set the two rows (a one-line `project.md` PR, or in this PR if you do it before the build ends). The bot-author acceptance check is proved then, not in this PR.
- **The commit email uses the bot's user id, not the app id.** The ticket says `<app-id>+<slug>[bot]@users.noreply.github.com`, but GitHub links a commit to a bot through the bot account's user id, which differs from the app id. The helper looks it up from `GET /users/<slug>[bot]`.
- **Team tickets filed by the bot are trusted by exact login.** Without this, the tracker's author check would reject every ticket the team files, because app bots aren't collaborators.
- **Bot login forms.** `gh` shows a bot author as `<slug>`, `<slug>[bot]` or `app/<slug>` depending on the field. The matcher accepts all three for the configured slug only. The build checks which form each field really returns against a real comment once the app exists, and drops forms that never appear. GitHub doesn't let an app take a name already used by another account, so a user can't post as `<slug>`.
- **`gh.sh` fails instead of falling back** when the app is configured but the token can't be minted, so a broken setup doesn't post as the owner.
- **Owner calls opt out with `AGENT_GH_AS=owner`,** set by `merge_pr.py` and `cos_approve_pr.py` themselves. A separate wrapper script would work too; the variable keeps one entry point.
- **A new `scripts/git.sh`** for commit and push, rather than asking every role to pass `-c user.name` and a credential helper by hand. It is plain `git` when no app is set.
- **Checks and Commit statuses (read) added** to the app's permissions on top of the ticket's list, because `wait-for-ci.sh` and `cos_brief.py` read check results through `gh.sh`.
- **JWT signed with the `openssl` CLI,** not a Python crypto package, to keep the scripts stdlib only.
- **Key at `~/.config/agent-team/<slug>.pem` or `$AGENT_GH_APP_KEY`,** never in `project.md`, and the helper refuses a key inside the repo or one readable by others.
- **No token cache.** Each `gh.sh` call mints a token (two API calls). A cache would mean a file or a long-lived process; the ticket forbids the file and the cost is small.

## Verification

`python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`, and `git grep -nE 'BEGIN (RSA )?PRIVATE KEY|ghs_[A-Za-z0-9]'` returns nothing.
