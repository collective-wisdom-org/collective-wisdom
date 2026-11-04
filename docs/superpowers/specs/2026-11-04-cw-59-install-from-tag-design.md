# CW-59: Install from a pinned tag so an app update is one command

**Ticket:** [CW-59](https://github.com/dbeallor/collective-wisdom/issues/59)
**Status:** Shipped
**Shipped:** in PR #70, with differences: [as-built](../as-built/2026-11-04-cw-59-install-from-tag.md)

## Goal

- Releases of this repo get tags, `v0.1`, `v0.2` and so on, each on a commit of `origin/main`.
- An app moves to a tag with one command run in the app, with no clone of this repo on the machine: `scripts/agent-team-update.sh v0.4`.
- `installed-from.txt` records the tag next to the SHA, so the install PR shows which release the app is on.
- The local-clone path (`install.sh`, `--to`, `--update`, `--check`) keeps working as it does today.

## Non-goals

- Opening the app's install PR automatically.
- Tagging from CI, or tagging on every merge.
- Release notes per tag, GitHub Releases, or a changelog file.
- Changing which files the installer copies, seeds or leaves alone.
- A first install with no clone. An app's first install still runs `install.sh` from a clone (or from the temp clone a one-off `git clone` makes); every update after that is the one command.

## Today

Facts from `main` at `08ae458`.

- `install.sh [--dry-run] [--to <ref>] <app>`, `--update [--to <ref>] [--force]` and `--check` (CW-42). Files come from `git archive <sha> agent-team` of this clone, the SHA must be on `origin/main`, and the clone must be its own repo root.
- `installed-from.txt` is one line, `collective-wisdom <40-character SHA>`. `install.sh` parses it with `^collective-wisdom ([0-9a-f]{40})$` and exits 2 on anything else. Nothing else in the repo reads it.
- No tags exist. `--update` without `--to` moves to `origin/main`.
- `install.sh` lives at the repo root and is not copied into apps. Apps get `agent-team/scripts/*` as `scripts/*`.
- `ship-loop` § Team mode "Workflow files" says the app's install PR "runs `install.sh --update` and so bumps `docs/agents/installed-from.txt`". README § Propose changes says the same.
- The repo is private, so any clone needs the user's git credentials for GitHub.

## Design

### 1. Tagging a release

New root script `tag-release.sh`, next to `install.sh` and, like it, never copied into apps.

```sh
./tag-release.sh            # tag origin/main with the next v0.N and push the tag
./tag-release.sh --dry-run  # print the tag it would make
```

It runs `git fetch -q --tags origin`, takes the commit at `refs/remotes/origin/main`, and picks the next number: the highest `N` among tags matching `v0.<N>` (numeric, so `v0.10` follows `v0.9`), plus one, or `v0.1` when there are none. It refuses when `origin/main` already carries a `v0.N` tag ("nothing new since v0.N"). Otherwise it makes an annotated tag (`git tag -a v0.N <sha> -m "collective-wisdom v0.N"`) and pushes only that tag (`git push origin refs/tags/v0.N`). It never touches a branch.

The user runs it by hand after a batch of merges they want apps to take. Pushing a tag is the user's step: no skill tells an agent to run it.

### 2. `install.sh --from <tag>`

```sh
./install.sh [--dry-run] --from <tag> <app>
./install.sh [--dry-run] --update --from <tag> [--force] <app>
```

`--from <tag>` is `--to` for a tag, with two differences:

- It fetches `origin/main` and that one tag from `origin` first (`git fetch -q --no-tags origin main "+refs/tags/<tag>:refs/tags/<tag>"`), so a stale or hand-made local tag of the same name is replaced by the remote one.
- It looks the tag up by its exact ref, `refs/tags/<tag>`, never by a guessed name, and records it in the pin.

`--from` and `--to` can't be used together, and neither goes with `--check`. A tag name starting with `-` or failing `git check-ref-format` is refused. The existing rules then apply unchanged: the tagged commit must be on `origin/main`, files come from `git archive` of it, and an update refuses on drift unless `--force`.

### 3. The pin records the tag

`installed-from.txt` gains an optional third field:

```
collective-wisdom <40-character SHA> v0.4
```

An install with `--from` writes it; an install with `--to` or neither writes the old two-field line, so a pin never names a tag the files didn't come from. The parser accepts both (`^collective-wisdom ([0-9a-f]{40})( (v0\.[0-9]+))?$`), so every existing pin still works. Only the SHA is used to find the old files.

The tag shows up in the reports:

- `--update`: `collective-wisdom v0.3 1a2b3c4d5e6f -> v0.4 9f8e7d6c5b4a (14 commits)`. A side with no tag shows the short SHA alone, as today.
- `--check`: `check: matches collective-wisdom <sha> (v0.3)` and `check: drift in N file(s) against collective-wisdom <sha> (v0.3)`.
- "already at" compares the whole pin line, so re-running `--from v0.4` on an app pinned to the same SHA without a tag rewrites the pin to add it.

### 4. The one command, from the app

New shipped script `agent-team/scripts/agent-team-update.sh`, so every app has `scripts/agent-team-update.sh` after its next install.

```sh
scripts/agent-team-update.sh [--dry-run] [--force] [<tag>]
```

Run from anywhere inside the app. It:

1. Finds the app with `git rev-parse --show-toplevel` in the current directory, like the other scripts (CW-42 `app_root.py`). It refuses when that repo has `install.sh` and `agent-team/` at its top: that is collective-wisdom itself, which updates by merging, not by installing.
2. Clones this repo into a temp folder (`git clone -q --no-checkout`). The URL is `https://github.com/dbeallor/collective-wisdom.git`, or `$COLLECTIVE_WISDOM_REPO` when set (another fork, an SSH URL, or a local path in tests). A failed clone says to check git credentials for GitHub (`gh auth setup-git`) and exits 1.
3. Picks the tag: the one given, or with none the highest `v0.N` among tags on `origin/main` (`git tag --merged origin/main`). No such tag exits 1.
4. Checks out that tag and runs the tag's own `install.sh --update --from <tag>` on the app, passing `--dry-run` and `--force` through. The installer that runs is the one that shipped with that release, so the result doesn't depend on what the app's copy of the wrapper is.
5. Removes the temp folder on exit and exits with the installer's code.

The wrapper needs the app's pin, so it only updates. Without `installed-from.txt` the installer's existing refusal says to run a plain install first.

### 5. The install PR

The app's install PR runs the command and records it, and the tag, in its body:

```
Ran: scripts/agent-team-update.sh v0.4
Pin: collective-wisdom <sha> v0.4
```

`ship-loop` § Team mode "Workflow files" changes from "runs `install.sh --update`" to "runs `scripts/agent-team-update.sh <tag>` (or `install.sh --update` from a clone) and puts the command in the PR body". Only the wording of how the install PR is made changes; the two-PR rule doesn't.

### 6. Docs

- `README.md`: § Install gains `--from` and the first-install-without-a-clone recipe (`git clone` into a temp folder, run its `install.sh --from <tag> <app>`). § Update leads with `scripts/agent-team-update.sh` and keeps the clone commands. A new § Releases covers `tag-release.sh`. § Propose changes: after merging, tag a release, then each app runs the one command. The pin format line shows the optional tag. The file list at the top names `tag-release.sh`.
- `ship-loop` § Team mode, Workflow files: § 5 above.
- `agent-team/templates/AGENTS.md`: the line about where the team comes from names `scripts/agent-team-update.sh` as the way to update.
- `docs/agents/project.md` (local) and `.github/workflows/ci.yml`: the shellcheck line adds `tag-release.sh`. The new wrapper is already covered by `agent-team/scripts/*.sh`.

## Tests

Per `AGENTS.md` § Testing: one table-driven test per rule, in `agent-team/scripts/test_install.py`, reusing its throwaway world. The fixture gains tags pushed to the bare `origin`: `v0.1` on commit A, `v0.2` on B, and `v0.9` on the unmerged commit S.

- **`--from` cases**, one table: install `--from v0.1` pins `<A> v0.1`; update `--from v0.2` from that pin reports `v0.1 ... -> v0.2 ...` and pins `<B> v0.2`; `--check` on a tagged pin passes and names the tag; `--from v0.9` (not on `origin/main`) refuses; `--from v0.7` (no such tag) refuses; a local `v0.2` tag pointing at S is replaced by origin's; `--from` with `--to` refuses. Each checks the exit code and the pin line.
- **Wrapper cases**, one table: from inside the app with `COLLECTIVE_WISDOM_REPO` pointing at the bare origin, no tag moves to `v0.2` (skipping `v0.9`, which isn't on `origin/main`); an explicit `v0.1` pins `v0.1`; `--dry-run` writes nothing; run inside a collective-wisdom checkout refuses. The temp folder is gone afterwards.
- **Tag script cases**, one table, against a throwaway clone with a bare origin: no tags makes `v0.1`; `v0.1` and `v0.9` existing makes `v0.10`; `origin/main` already tagged refuses; `--dry-run` pushes nothing. Each checks the tag on the origin.

Existing `test_install.py` cases keep passing unchanged: they cover the local-clone path and the two-field pin.

## Calls I made

- **The one command is a shipped wrapper, `scripts/agent-team-update.sh`, not a `curl | bash` line.** The repo is private, so raw downloads need a token; a `git clone` uses the credentials the user already has for GitHub.
- **Tagging is by hand, with `tag-release.sh`, not from CI.** The ticket allows either. By hand keeps "a batch" the user's call and needs no workflow with write access to the repo.
- **The wrapper only updates.** A first install still needs `install.sh` from a clone, which a one-off `git clone` into a temp folder covers; README shows it.
- **`--update` with no `--from` or `--to` still moves to `origin/main`**, not the newest tag, so the local-clone path doesn't change.
- **The wrapper runs the tag's own `install.sh`**, not a copy in the app, so the installer and the files always come from the same release.
- **With no tag given, the wrapper takes the highest `v0.N` on `origin/main`.** A hand-made tag on an unmerged commit is skipped. Named explicitly, that tag is refused by the installer's `origin/main` rule.
- **A pin records a tag only when the install used `--from`.** `--to v0.4` installs the same commit but writes the two-field line.
- **Tags are `v0.N` only.** No `v1`, no patch numbers. The parser and the wrapper's tag pick accept only that shape.
- **The wrapper refuses to run in collective-wisdom itself**, where `scripts/` is a link into `agent-team/` and an install would write through it.
- **The default source URL is hardcoded in the wrapper**, with `$COLLECTIVE_WISDOM_REPO` to override it. Recording the URL in the pin was left out.

## Risks

- A clone needs GitHub credentials for a private repo. A machine where `git clone https://github.com/...` fails needs `gh auth setup-git` (or an SSH URL in `$COLLECTIVE_WISDOM_REPO`). The wrapper's error says so.
- The wrapper runs code from the tag it clones. That is the same trust as running `install.sh` from a clone today; the tag must be on `origin/main`, which only merged PRs reach.
- A tag can be moved or deleted on the remote by anyone with push access. The pin keeps the SHA, so drift checks and updates still find the old files by SHA.
