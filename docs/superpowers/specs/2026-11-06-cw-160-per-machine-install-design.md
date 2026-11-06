# CW-160: install the agent team once per machine

**Status:** Shipped
**Shipped:** in PR #164, as specified
**Ticket:** [#160](https://github.com/collective-wisdom-org/collective-wisdom/issues/160)

## Goal

One clone of collective-wisdom on a machine runs the agent team in every repo that person has cloned, all on the clone's checkout. Updating that clone is the one update for every repo.

## Today

- `install.sh` copies `.claude/skills`, `.claude/agents`, `.claude/mods`, `scripts` and `docs/agents` into each app and pins it with `docs/agents/installed-from.txt`.
- Skills, role docs and templates call scripts as `./scripts/<name>` or `python3 scripts/<name>` (about 250 call sites), so they need a copy of `scripts/` in the app.
- The Stop hook in `agent-team/.claude/settings.json` runs `$CLAUDE_PROJECT_DIR/scripts/cos_rotation_check.py --hook`.
- `cos_rotation_check.skill_commit()` runs `git log` on `SKILL_PATHS` inside the app repo (`ROOT`).
- Scripts already find the app through `app_root.root()` (the git top level of the cwd), and find each other (`gh.sh`, `load_module`) next to their own file. So a script run from anywhere serves the app it is run in.
- Claude Code loads user skills from `~/.claude/skills/<name>`, user subagents from `~/.claude/agents/<name>.md`, user hooks from `~/.claude/settings.json` and user instructions from `~/.claude/CLAUDE.md`. Codex loads `~/.agents/skills/<name>` and `~/.codex/AGENTS.md`. Cursor loads `~/.cursor/skills/<name>`; its user rules live in its settings screen, not in a file.

## Builds

1. **`install.sh` becomes the machine install.** There is one install script. Run from a clone with no target path (`./install.sh`, or `./install.sh --dry-run`), it installs that clone for the machine. A target path (`./install.sh /path/to/app`, with `--update`, `--check`, `--to`, `--from`) still runs the old copy-into-an-app code, untouched, until CW-161 deletes it; this ticket adds the machine mode beside it and does not change it. The machine mode:
   - Refuses unless the clone is its own git repo root and not a linked worktree (a T3 or `.worktrees/` checkout goes away, and its links would dangle).
   - Links `~/.collective-wisdom` to `<clone>/agent-team`. This is the one fixed path every call site uses.
   - Links each skill folder in `agent-team/.claude/skills/` into `~/.claude/skills/`, `~/.agents/skills/` and `~/.cursor/skills/`, and each subagent file in `agent-team/.claude/agents/` into `~/.claude/agents/`. One link per skill or agent, so the person's own skills in those folders stay.
   - Never replaces a real file or folder, or a link that points somewhere else. It skips that name and lists it under `TODO:` with the path, so the person decides.
   - Removes its own links that now dangle (they point into this clone and the target is gone), so a skill dropped in a newer release goes away on the next run. It touches no other link.
   - Adds the Stop hook to `~/.claude/settings.json`: `python3 "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true`. It parses the file as JSON, adds the entry only when no hook command already mentions `cos_rotation_check.py`, keeps every other key, and writes through a temp file and rename. A missing file is created. A file that is not valid JSON, or whose `hooks.Stop` is not a list, is left alone and the hook goes under `TODO:`.
   - Writes the user-level instruction into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`, as one block between `<!-- collective-wisdom:begin -->` and `<!-- collective-wisdom:end -->`. A rerun replaces the block; text outside it is never touched. A file with only one of the two marker comments is left alone and listed under `TODO:`. For Cursor it prints the same text under `TODO:` to paste into Cursor's user rules.
   - `--dry-run` prints every change and writes nothing. Every write is printed. It writes only under `$HOME` in the paths above, so a test can point `HOME` at a temp folder. No other flag goes with it (`--to`, `--from`, `--update`, `--check`, `--force` need a target path, as today).
   - Ends with `installed collective-wisdom <sha> [<tag>] from <clone>` and the TODO list. A `--dry-run` ends with `would install collective-wisdom <sha> [<tag>] from <clone>` instead.
   - It does not touch any app. Putting the project stub in a repo is the later set-up command's job (see Leaves out).
2. **The instruction text**, kept in `agent-team/templates/machine-instruction.md` so the script and the docs share one copy: the agent team runs only in a repo that has `docs/agents/project.md`; in a repo without it the team is not running, so don't start its skills or run its scripts there.
3. **Call sites use the clone's scripts.** In `agent-team/.claude/skills/`, `agent-team/docs/agents/` and `agent-team/templates/`, every `./scripts/<name>` and `scripts/<name>` that tells an agent to run a script becomes `~/.collective-wisdom/scripts/<name>`. Hint lines that scripts print telling the agent to run another script change the same way. Prose that names the `scripts/` folder as a place (the approval path list, "a PR that touches any script") stays.
4. **The Stop hook does nothing outside the team.** `cos_rotation_check.py --hook` exits 0 silently when the repo it runs in has no `docs/agents/project.md`, before it reads anything else.
5. **`skill_commit()` reads the clone's history.** `SKILL_PATHS` resolve against the folder above the script's own `scripts/` folder (`<clone>/agent-team` through `~/.collective-wisdom`), and `git log` runs there, not in the app. `branch()` still reads the app.
6. **Docs.** A `## Install on a machine` section in `README.md`, placed before `## Install` (install, update by checking out a newer release in the clone and running `./install.sh` again, what it links, the TODO cases). It says `## Install` and `## Update` below describe the older copy-into-an-app route until CW-161 removes it; those two sections are not edited. The README's "Running a Chief of Staff in this repo" says to run `./install.sh` from the root checkout here. The `Layout` bullet for `install.sh` gains the machine mode. The tests go in a new `test_install_machine.py`, not in `test_install.py`.
7. **Lint and approval path.** Nothing to add: `install.sh` is already in the shellcheck list and on the approval path.
8. **Tests**, table-driven per `AGENTS.md` § Testing:
   - `./install.sh` (no target) against a temp `HOME`: fresh install links everything and adds the hook; a rerun changes nothing; an existing settings file keeps its keys; a real folder and a foreign link of a shipped name are kept and listed; a dangling link into the clone is removed and a dangling foreign link is kept; the instruction block is replaced, not duplicated; a linked worktree is refused.
   - Rotation check: the hook is silent in a repo with no `project.md`; the skill commit follows the clone's history and does not need those paths in the app's history.
   - A layout check that no skill, role doc or template still calls a script as `./scripts/<name>` or bare `scripts/<name>.(py|sh)`.

## Acceptance (from the ticket)

- With the install present, a Chief of Staff skill is invocable in a repo with no `.claude/skills` (user-level skill link).
- `~/.collective-wisdom/scripts/<x>.py` run with cwd in an app reads that app's `docs/agents/project.md` (`app_root.root()`, unchanged).
- The skill commit changes when the clone's skill files change, and does not depend on the app's history.
- The Stop hook does not block a stop in a repo with no `project.md`.
- Two repos run the clone's checkout, with no separate pin.

## Leaves out

- Any change to the app-target modes of `install.sh`, to `agent-team-update.sh`, `agent-team/.claude/settings.json`, `agent-team/templates/gitignore`, the pin or anything an app commits. CW-161 changes those.
- Putting `docs/agents/project.md` in a repo. That is the later set-up command (the ticket's out of scope line), which walks the user through adding the project stub as a PR. No part of `install.sh`'s machine mode seeds or edits an app.
- Role doc reads (`docs/agents/<role>.md` in skills and subagent files). CW-161 moves them to the machine install; until then apps still have the copies.
- This repo's root links into `agent-team/`, `mods/agent-gantt`, the marketplace and the status pane.
- Choosing the GitHub account, and the `set up this repo` command itself.

## Calls I made

- **This repo needs the machine install too.** Skills here will call `~/.collective-wisdom/scripts/`, so a Chief of Staff in this repo needs `./install.sh` run once from the root checkout. Worktrees then run main's scripts and skills, not their branch's. The root links stay as they are. This is the one change to how development works here, and it matches the rule that only workflow on the merge target counts.
- **User-level skills win over an app's old copies.** Claude Code prefers a personal skill to a project skill of the same name, so once the machine install exists, an app still pinned to an older release runs the clone's skills. That is the ticket's goal (one release per machine), but an app's pin stops meaning anything before CW-161 removes it.
- **One script, `install.sh`, whose no-target form is the machine install.** The first review asked for a single install script, not a second one. The old app-target forms stay in the same file, unchanged, only so that apps keep a working update path until CW-161 removes them. This means CW-160 and CW-161 both edit `install.sh`; CW-161 is already blocked by CW-160, so it starts from this ticket's merged file.
- **What CW-161 must now do.** (1) Delete the app-target forms from `install.sh`: the copy, `--update`, `--check`, `--to`, `--from`, `--force`, the pin, drift, `shipped()` and `sync_dir`, leaving the machine install as the whole script, and delete `agent-team-update.sh`. (2) Stop seeding `docs/agents/project.md` and `AGENTS.md` from `install.sh`: its CW-161 ticket text says `install.sh` still seeds the stub and adds the `.gitignore` line, which no longer holds, because the install touches no app. That work, and the removal of an app's old copied team files, moves into the set-up command, which walks the user through a PR in the app containing only the stub (`docs/agents/project.md` plus the `.agent-team/` line in `.gitignore`) and deleting the old copies. (3) The Chief of Staff should re-scope CW-161 on that basis, or split the set-up command into its own ticket; I did not edit either ticket.
- **Script names for the other tickets to rely on.** `./install.sh` (no target) is the only supported install after CW-161; the machine mode and its tests (`test_install_machine.py`) are not touched by CW-161 except by deleting the old code around them.
- **`~/.collective-wisdom` links to the clone's `agent-team/` folder, not the clone root,** so call sites read `~/.collective-wisdom/scripts/gh.sh`, the same depth as `./scripts/gh.sh` today. Not `~/.agent-team`, which an app uses for its state folder.
- **Update is checkout plus rerun.** No update command. Checking out a newer tag in the clone updates every repo at once; the rerun (`./install.sh`) only adds new skill links and drops dead ones. The script does not require a tag checkout, so the root checkout here (on `main`) can be the install.
- **Name conflicts are skipped, not overwritten.** A person's own `implementer` agent or `human-writing` skill wins, and the TODO names it.
- **Two Stop hooks in old apps.** An app with the old project-level hook runs both until someone removes it (CW-161 leaves existing settings alone). Both are read only and give the same answer, so the worst case is the rotation reason shown twice.
- **Cursor gets a printed instruction**, since its user rules have no file to write.

## Touches

none of: data, money, auth, user email, migrations. It writes outside the repo, under `$HOME` (`~/.claude`, `~/.agents`, `~/.cursor`, `~/.codex`, `~/.collective-wisdom`), so the security review checks those writes.
