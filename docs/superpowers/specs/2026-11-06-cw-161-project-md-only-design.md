# CW-161: Leave only project.md from the team in a consuming repo

**Ticket:** [CW-161](https://github.com/collective-wisdom-org/collective-wisdom/issues/161)
**Status:** Spec (revised for CW-160's one-script design)
**Follows:** CW-160 (install the team once per machine). This ticket builds on CW-160's merged `install.sh` and `~/.collective-wisdom` path, and merges after it.

## Goal

An app commits `docs/agents/project.md` and nothing else from the team. Skills, agents, scripts and shared role docs come from the machine install (CW-160). `install.sh` is only the machine install: it no longer copies into, seeds or updates an app. An app installed the old way has one command that removes its copies and its pin.

## How the work divides

- **CW-160:** `install.sh` with no target is the machine install. It links `~/.collective-wisdom` to `<clone>/agent-team`, links skills and agents, adds the user Stop hook, writes the user instruction and rewrites script call sites to `~/.collective-wisdom/scripts/<name>`. It leaves the old app-target forms of `install.sh` in place, unchanged.
- **CW-161 (this ticket):** deletes those app-target forms and `agent-team-update.sh`; adds the removal command for old apps; moves role-doc reads to the machine install; moves the status pane to the marketplace route; updates the docs.
- **The init step** (the later set-up command, CW-163 or the ticket the user puts it in): walks the user through a PR in the app that adds `docs/agents/project.md` and the `.agent-team/` line in `.gitignore`. It is not built here, and nothing here seeds `project.md` or edits `.gitignore`. It can call this ticket's removal command when it finds a pin.

## Non-goals

- Anything CW-160 builds (the machine mode of `install.sh`, the links, the hook, the user instruction, script call sites).
- Writing `project.md` or the `.gitignore` line, by script or by interview (the init step).
- Removing the `Owner login` row (CW-162).
- Rewriting an app's `AGENTS.md`, or stripping the old Stop hook out of an app's `.claude/settings.json`.
- This repo's root links into `agent-team/`, and `mods/agent-gantt`.

## Today

Facts from `main` at `b923e59` and CW-160's spec (branch `feat/cw-160-per-machine-install` at `6ce4af2`).

- `install.sh <app>` (with `--update`, `--check`, `--to`, `--from`, `--force`, `--dry-run`) copies `agent-team/.claude/{skills,agents,mods}`, `agent-team/scripts` and `agent-team/docs/agents` into the app (`shipped()`, `sync_dir`), writes the pin `docs/agents/installed-from.txt`, seeds `project.md`, `AGENTS.md`, `settings.json` and `docs/superpowers/README.md` when missing, creates `.agents/skills -> ../.claude/skills`, and appends `templates/gitignore`. After CW-160 it also has the no-target machine mode.
- `agent-team/scripts/agent-team-update.sh <tag>`, run in an app, clones this repo and runs the tag's `install.sh --update --from <tag> <app>`.
- Skills, role docs, templates and the five `.claude/agents/*.md` pointers name role docs as `docs/agents/<file>.md`, a path in the app (about 45 references in 22 files, plus `trackers/`). CW-160 leaves these.
- `status-pane` ships in `.claude/mods/` and is in `.claude-plugin/marketplace.json`.
- `cos_state.DEFAULT_FILE` is `.agent-team/state.json` under `app_root.root()`, the app's git toplevel. Nothing here changes it.

## Design

### 1. `install.sh` is the machine install only

Delete the app-target code: the target path argument, `--update`, `--check`, `--to`, `--from`, `--force`, the pin, `extract`, `shipped`, `drift`, `sync_dir`, `seed_file`, the dirty check, the seeding of `project.md`, `AGENTS.md`, `settings.json` and `docs/superpowers/README.md`, the `.agents/skills` link and the `.gitignore` append. What CW-160 built stays as it merged.

A leftover target path or app flag exits 2 with: `install.sh no longer installs into an app. Run ./install.sh with no path to install on this machine. To remove an old copy from an app, run ~/.collective-wisdom/scripts/remove_app_copies.py in it.` That covers old apps whose `agent-team-update.sh` calls `install.sh --update --from <tag> <app>`.

Delete `agent-team/scripts/agent-team-update.sh`. Its only job was the app-target update.

### 2. Removal command for old apps

New `agent-team/scripts/remove_app_copies.py [--dry-run] [--force]`, run with cwd in the app (`app_root.root()`). It writes nothing outside the app and never commits.

- No `docs/agents/installed-from.txt`: print `nothing to remove: no installed-from.txt` and exit 0.
- Parse the pin as today (`collective-wisdom <40-hex SHA> [v0.N]`); a malformed pin exits 2.
- The pinned commit must be in the clone (the repo above the script's own `agent-team/scripts/`, symlinks resolved). If not, exit 2 with `run 'git fetch origin' in <clone>`.
- List the files the pinned commit's `agent-team/` has under `.claude/skills`, `.claude/agents`, `.claude/mods`, `scripts` and `docs/agents` (today's `shipped()` rule, read with `git ls-tree` at that commit), minus `docs/agents/project.md`.
- A listed file in the app that differs from the pinned copy (edited by hand) stops the run with the list and exit 1, unless `--force`. A listed file already missing is fine.
- Delete each listed file that exists, then the pin, printing `remove  <path>` for each. Remove directories left empty under those five roots; a directory with the app's own files stays. Remove `.agents/skills` when it is a link to `../.claude/skills` and `.claude/skills` is gone, and `.agents` if that leaves it empty.
- If `.claude/settings.json` mentions `cos_rotation_check.py`, print a TODO: the machine install runs that hook now, so remove it from this file by hand. Also a TODO to commit the removal as a PR in the app.
- `--dry-run` prints the same lines and writes nothing.
- Refuse (exit 1) when run in collective-wisdom itself (`install.sh` and `agent-team/` at the top), as `agent-team-update.sh` does today.

### 3. Role docs from the machine install

In `agent-team/.claude/skills/`, `agent-team/.claude/agents/`, `agent-team/docs/agents/` and `agent-team/templates/`, every reference that tells an agent to read a shared role doc, `docs/agents/<path>` other than `project.md`, becomes `~/.collective-wisdom/docs/agents/<path>`, the same way CW-160 moved script call sites. `docs/agents/project.md` stays: it is the app's file. Prose that names `docs/agents/` as a place (the approval path list, "any role doc under `docs/agents/`", review scope) stays.

CW-160's layout check (no `./scripts/<name>` call sites) gains a row: no shared role doc read as a bare `docs/agents/<file>.md` other than `project.md`. One table, not a new test.

### 4. Status pane from the marketplace

`README.md` and `agent-team/docs/agents/status-pane.md` say to install it with `claude plugin install status-pane --marketplace collective-wisdom-org/collective-wisdom`, and drop the copied route. The mod's files and the marketplace entry don't change. The removal command takes out an old copy (it is under `.claude/mods`).

### 5. Docs

- `README.md`: delete the app-target `## Install`, `## Update` and check sections, the pin text, `agent-team-update.sh` and the "a future installer must keep accepting that call" note. Add `## Moving an app off the copied team` (run the removal command, open a PR; the init step adds `project.md` if it is missing). The layout bullets say an app commits only `project.md`.
- `ship-loop` § Workflow files: a workflow change ships through a PR here, then a newer checkout in the machine clone. No app install PR, no `installed-from.txt`. Edit the paragraph as CW-160 left it.
- `agent-team/docs/superpowers/README.md`: drop the `install.sh --update <app>` line.

## Acceptance

Re-scoped from the ticket now that `install.sh` touches no app (see Calls):

- After the removal command, an old app shows no copied skills, scripts, agents, mods or role docs, no pin and no `.agents/skills` link; `project.md`, `AGENTS.md`, `settings.json`, `.gitignore` and an app-owned file under `.claude/skills/` are byte for byte unchanged.
- A hand-edited copy stops the removal and nothing is written; `--force` removes it. `--dry-run` writes nothing.
- `install.sh <app>` and `install.sh --update --from v0.N <app>` exit 2 with the message above and write nothing.
- No skill, agent file, role doc or template reads a shared role doc from the app.
- `.agent-team/state.json` still resolves under the app: `cos_state.DEFAULT_FILE` and `app_root.root()` are unchanged, and their tests pass.
- The `.agent-team/` line in `.gitignore` and the `project.md` stub come from the init step, not from this ticket.

## Testing

- `test_install.py`: drop the app-target cases (install and update, existing setup, check, from tag, wrapper). Keep `test_tag_release`. Add one row to CW-160's `install.sh` tests: a target path exits 2 and writes nothing.
- New `test_remove_app_copies.py`, one table-driven test: no pin; clean old app; app-owned files kept; hand edit with and without `--force`; dry run; malformed pin; pinned commit missing from the clone; run inside collective-wisdom.
- The layout check row from § 3.
- Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Calls I made

- **Must merge after CW-160, and the build starts after it merges.** CW-161 deletes the app-target half of `install.sh` that CW-160 leaves in place, and uses CW-160's `~/.collective-wisdom` path for role docs and the removal command. The two don't edit the same lines: CW-160 adds the no-target machine mode, CW-161 removes the code around it. The build starts by rebasing on `main` after CW-160 merges, and stops with `BLOCKED:` if it hasn't.
- **The ticket's "`install.sh` still seeds `project.md` and the `.gitignore` line" no longer holds.** Under the new design `install.sh` touches no app, so that moves to the init step's PR. This ticket builds none of it. Its acceptance lines about `project.md` and `.gitignore` are met by the init step.
- **Removing old copies is a separate script, not part of `install.sh`,** because `install.sh` is machine only. The init step can call it when it finds a pin; until then the README tells people to run it.
- **Old apps' `agent-team-update.sh` gets a clear error, not a silent removal.** Their copy calls the new tag's `install.sh --update`; doing the removal there would put app writes back into `install.sh`.
- **`agent-team-update.sh` is deleted,** since there is no app-target install left to call.
- **Role-doc paths are rewritten, not mapped by a rule.** This matches how CW-160 moves script calls, and an agent follows a concrete path more reliably. It earlier looked like a conflict risk; building after CW-160 merges removes it.
- **Hand-edited copies stop the removal unless `--force`,** so local edits are never lost silently.
- **The removal command lists files from `git ls-tree` at the pinned commit,** not an extracted copy, and compares blob content. Same rule as `shipped()`, less disk churn.
- **`AGENTS.md`, `settings.json` and `docs/superpowers/README.md` in an app are never touched.** The old Stop hook gets a TODO only.
