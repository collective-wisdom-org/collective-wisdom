# CW-161: Leave only project.md from the team in a consuming repo

**Ticket:** [CW-161](https://github.com/collective-wisdom-org/collective-wisdom/issues/161)
**Status:** Spec
**Follows:** CW-160 (install the team once per machine). This ticket builds on CW-160's install and merges after it.

## Goal

An app commits `docs/agents/project.md` and nothing else from the team. Skills, agents, mods, scripts and shared role docs come from the per-machine install (CW-160). `install.sh` on an app seeds `project.md` and the `.gitignore` lines, and on an app installed the old way it removes the copies and the pin.

## Non-goals

- Building the per-machine install, its user-level instruction or its Stop hook (CW-160).
- Removing the `Owner login` row (CW-162).
- Rewriting an app's `AGENTS.md`, or stripping the old Stop hook out of an existing `.claude/settings.json`.
- Filling `project.md` by interview (CW-163).
- This repo's root links into `agent-team/`.
- `agent-team-update.sh` itself. It still runs a tag's `install.sh --update --from <tag> [--dry-run] [--force] <app>`, and that call keeps working.

## Today

Facts from `main` at `b923e59`.

- `install.sh` `sync_dir` copies `agent-team/.claude/{skills,agents,mods}`, `agent-team/scripts` and `agent-team/docs/agents` into the app, overwriting. `shipped()` lists those same paths.
- It writes `docs/agents/installed-from.txt` (`collective-wisdom <sha> [v0.N]`). `--update` and `--check` refuse without it. `--update` runs a drift check against the pinned commit and refuses on hand-edited copies unless `--force`; `--update --from` also refuses a tag older than the pin.
- It adds `.claude/settings.json` (the Stop hook) when missing, or a TODO to merge the hook by hand. It adds `docs/superpowers/README.md` when missing. It seeds `project.md` and `AGENTS.md` when missing and checks an existing `AGENTS.md` for four sections. It creates the `.agents/skills -> ../.claude/skills` link when missing.
- It appends the missing lines of `agent-team/templates/gitignore` (which has `.agent-team/`).
- On `--update` it lists files the old pin shipped and the new commit does not, as "Delete" TODOs.
- `status-pane` is copied under `.claude/mods/` and is also in `.claude-plugin/marketplace.json`.
- Skills and agent files point at role docs as `docs/agents/<file>.md`, a path in the app (about 45 references, plus `trackers/`).
- `cos_state.DEFAULT_FILE` is `.agent-team/state.json` under `app_root.root()`, the app's git toplevel. Nothing here changes it.

## Design

### Install (plain or `--update`)

One flow. `--update` is still accepted and does the same as a plain install, so the `agent-team-update.sh` call keeps working.

1. Resolve the commit as today (`--to`, `--from`, HEAD, or `origin/main` for `--update`; must be on `origin/main`). It now only supplies the templates.
2. Refuse on uncommitted changes in the paths it touches (`.claude`, `scripts`, `docs/agents`, `.agents`, `.gitignore`), as today.
3. **Remove the old copies** when `docs/agents/installed-from.txt` exists:
   - Extract the pinned commit, as today, and take its `shipped()` list.
   - Drift check against that commit, as today. A copy that differs from the pin (edited by hand) stops the run with the list, unless `--force`. A shipped file already missing is fine.
   - Delete every file in the list except `docs/agents/project.md` (never in `shipped()` today, but excluded by name too). Then delete the pin. Each deletion prints `remove  <path>`.
   - Remove directories left empty under `.claude/skills`, `.claude/agents`, `.claude/mods`, `scripts` and `docs/agents`. A directory with the app's own files stays.
   - Remove `.agents/skills` when it is the link `../.claude/skills` and `.claude/skills` is gone. Remove `.agents` if that leaves it empty.
   - A malformed pin, or a pinned commit this clone lacks, exits 2 as today, before anything is written.
4. Seed `docs/agents/project.md` from `templates/project.md` when missing. Never touch an existing one.
5. Append the missing lines of `templates/gitignore`, as today.
6. If `.claude/settings.json` mentions `cos_rotation_check.py`, add a TODO: the machine install runs that hook now, so remove it from this file by hand. The file is never written.

Gone from the installer: copying skills, agents, mods, scripts and role docs; the old-copy skill-folder warning; adding `settings.json`; adding `docs/superpowers/README.md`; seeding `AGENTS.md` and its section check; creating or checking `.agents/skills`; writing the pin; the "Delete" TODOs; `--update --from` refusing an older tag (there is nothing to move backwards). `--force` is allowed with or without `--update`.

`--dry-run` prints what it would remove, seed and ignore, and writes nothing.

### Check

`install.sh --check <app>` writes nothing and answers "is this app down to project.md?". It prints `left  <path>` for each leftover: the pin, and any file in this clone's HEAD `shipped()` list that exists in the app. It also prints `missing  docs/agents/project.md` when that is absent. Exit 0 with `check: only project.md` when there is nothing to print, else exit 1 with `check: N leftover file(s)`.

### Role docs

The rule: in a skill or agent file, `docs/agents/project.md` is the app's file, and every other `docs/agents/<path>` is the team install's `agent-team/docs/agents/<path>`, at the location CW-160 sets. It is stated once in `ship-loop` § Repo invariants (every skill defers there) and once in each `.claude/agents/*.md` pointer, next to its role-doc path. The ~45 references stay as written. In this repo the two readings are the same file, through the root links.

### Status pane

The app no longer gets a copy. `README.md` and `agent-team/docs/agents/status-pane.md` say to install it from the marketplace (`claude plugin install status-pane --marketplace collective-wisdom-org/collective-wisdom`). The mod's own files and the marketplace entry don't change.

### Docs

- `README.md`: Install, Check, Update and the layout bullets describe the new flow, drop the pin, and say an app commits only `project.md`. The note that a future installer must keep accepting the wrapper's call stays.
- `ship-loop` § Workflow files: the app install PR no longer bumps `installed-from.txt`. If CW-160 has already reworded that paragraph, edit its version.
- `agent-team/docs/superpowers/README.md`: the line about `install.sh --update` moving an app to the newest commit.

## Acceptance

- Install on a fresh repo: the app shows `docs/agents/project.md` and `.gitignore` with `.agent-team/`, and no `.claude/skills`, `.claude/agents`, `.claude/mods`, `scripts`, other `docs/agents/` files, pin, `settings.json`, `AGENTS.md` or `.agents/skills`.
- `--update` on an app installed the old way (pin plus copies): the copies, the pin and the `.agents/skills` link are gone; `project.md`, `AGENTS.md`, `settings.json` and an app-owned file under `.claude/skills/` are byte for byte unchanged; `.gitignore` has `.agent-team/`.
- `--update` with a hand-edited copy refuses and writes nothing; with `--force` it removes it.
- `agent-team-update.sh <tag>` on an old app does the same as `--update --from <tag>`.
- `--check` exits 1 with `left` lines on an old app and 0 after the update.
- `.agent-team/state.json` still resolves under the app: `cos_state.DEFAULT_FILE` and `app_root.root()` are unchanged, and their existing tests pass.

## Testing

`agent-team/scripts/test_install.py` is rewritten around the new rules, one table-driven test each: install and update outcomes (fresh app, old app, drift with and without `--force`, existing `project.md` untouched, app-owned files kept, dry run writes nothing), `--check`, and the wrapper. `test_tag_release` stays. Cases that only covered copying, the pin or `AGENTS.md` sections go. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Calls I made

- **Merge after CW-160, and build on top of it.** Both change `install.sh`, `README.md` and `ship-loop`. This ticket touches only the per-app path of `install.sh` (copy, pin, seed, check), not anything CW-160 adds for the machine. The role-doc rule names CW-160's install location, which does not exist yet. So the build starts by rebasing on `main` after CW-160 merges; if CW-160 is not merged when the spec is approved, the build waits and says so.
- **`install.sh` stops seeding `AGENTS.md`.** The ticket says only `project.md` is committed from the team. An existing `AGENTS.md` is never touched. `templates/AGENTS.md` stays in this repo for anyone who wants to copy it by hand.
- **Hand-edited copies stop the update unless `--force`,** the same rule as today's drift check, so a removal never loses local edits silently.
- **`--update` and a plain install do the same thing.** Removal runs whenever a pin is present. `--update` is kept so old apps' `agent-team-update.sh` calls work.
- **Role docs are mapped by one rule, not by rewriting ~45 paths.** Less churn and fewer conflicts with CW-160, which edits the same skills for script paths.
- **`--check` is kept, with a new meaning:** leftover team files, not drift against a pin.
- **`.agents/skills` is removed** when it is the old link and `.claude/skills` is gone, since it would point at nothing.
- **`docs/superpowers/README.md` is no longer added, but an existing one stays.** It describes the app's own spec folders and is not in `shipped()`.
- **The old Stop hook gets a TODO, not an edit.** Stripping it is out of scope; it is harmless (`|| true`) but runs a script that is now gone.
- **`.gitignore` keeps the whole template,** not just `.agent-team/`: it only appends missing lines, as today.
