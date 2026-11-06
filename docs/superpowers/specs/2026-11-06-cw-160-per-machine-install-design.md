# CW-160: install the agent team once per machine

**Status:** Draft
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

1. **`install-machine.sh`**, a new script at the repo root next to `install.sh`. Run from a clone, it installs that clone for the machine:
   - Refuses unless the clone is its own git repo root and not a linked worktree (a T3 or `.worktrees/` checkout goes away, and its links would dangle).
   - Links `~/.collective-wisdom` to `<clone>/agent-team`. This is the one fixed path every call site uses.
   - Links each skill folder in `agent-team/.claude/skills/` into `~/.claude/skills/`, `~/.agents/skills/` and `~/.cursor/skills/`, and each subagent file in `agent-team/.claude/agents/` into `~/.claude/agents/`. One link per skill or agent, so the person's own skills in those folders stay.
   - Never replaces a real file or folder, or a link that points somewhere else. It skips that name and lists it under `TODO:` with the path, so the person decides.
   - Removes its own links that now dangle (they point into this clone and the target is gone), so a skill dropped in a newer release goes away on the next run. It touches no other link.
   - Adds the Stop hook to `~/.claude/settings.json`: `python3 "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true`. It parses the file as JSON, adds the entry only when no hook command already mentions `cos_rotation_check.py`, keeps every other key, and writes through a temp file and rename. A missing file is created. A file that is not valid JSON is left alone and the hook goes under `TODO:`.
   - Writes the user-level instruction into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`, as one block between `<!-- collective-wisdom:begin -->` and `<!-- collective-wisdom:end -->`. A rerun replaces the block; text outside it is never touched. For Cursor it prints the same text under `TODO:` to paste into Cursor's user rules.
   - `--dry-run` prints every change and writes nothing. Every write is printed. It writes only under `$HOME` in the paths above, so a test can point `HOME` at a temp folder.
   - Ends with `installed collective-wisdom <sha> [<tag>] from <clone>` and the TODO list.
2. **The instruction text**, kept in `agent-team/templates/machine-instruction.md` so the script and the docs share one copy: the agent team runs only in a repo that has `docs/agents/project.md`; in a repo without it the team is not running, so don't start its skills or run its scripts there.
3. **Call sites use the clone's scripts.** In `agent-team/.claude/skills/`, `agent-team/docs/agents/` and `agent-team/templates/`, every `./scripts/<name>` and `scripts/<name>` that tells an agent to run a script becomes `~/.collective-wisdom/scripts/<name>`. Hint lines that scripts print telling the agent to run another script change the same way. Prose that names the `scripts/` folder as a place (the approval path list, "a PR that touches any script") stays.
4. **The Stop hook does nothing outside the team.** `cos_rotation_check.py --hook` exits 0 silently when the repo it runs in has no `docs/agents/project.md`, before it reads anything else.
5. **`skill_commit()` reads the clone's history.** `SKILL_PATHS` resolve against the folder above the script's own `scripts/` folder (`<clone>/agent-team` through `~/.collective-wisdom`), and `git log` runs there, not in the app. `branch()` still reads the app.
6. **Docs.** A `## Install on a machine` section in `README.md` (install, update by checking out a newer release in the clone and running `install-machine.sh` again, what it links, the TODO cases). `CONTRIBUTING.md` or the README's "Running a Chief of Staff in this repo" says to run `./install-machine.sh` from the root checkout here.
7. **Lint and approval path.** `install-machine.sh` joins the shellcheck list in CI and in `project.md`'s `Lint` row, and joins `install.sh` and `tag-release.sh` on the approval path (`approval_policy.PATH_FILES` and `chief-of-staff/approvals.md` § Auto-approval).
8. **Tests**, table-driven per `AGENTS.md` § Testing:
   - `install-machine.sh` against a temp `HOME`: fresh install links everything and adds the hook; a rerun changes nothing; an existing settings file keeps its keys; a real folder and a foreign link of a shipped name are kept and listed; a dangling link into the clone is removed and a dangling foreign link is kept; the instruction block is replaced, not duplicated; a linked worktree is refused.
   - Rotation check: the hook is silent in a repo with no `project.md`; the skill commit follows the clone's history and does not need those paths in the app's history.
   - A layout check that no skill, role doc or template still calls a script as `./scripts/<name>` or bare `scripts/<name>.(py|sh)`.

## Acceptance (from the ticket)

- With the install present, a Chief of Staff skill is invocable in a repo with no `.claude/skills` (user-level skill link).
- `~/.collective-wisdom/scripts/<x>.py` run with cwd in an app reads that app's `docs/agents/project.md` (`app_root.root()`, unchanged).
- The skill commit changes when the clone's skill files change, and does not depend on the app's history.
- The Stop hook does not block a stop in a repo with no `project.md`.
- Two repos run the clone's checkout, with no separate pin.

## Leaves out

- `install.sh`, `agent-team-update.sh`, `agent-team/.claude/settings.json`, `agent-team/templates/gitignore`, the pin and anything an app commits. CW-161 changes those.
- Role doc reads (`docs/agents/<role>.md` in skills and subagent files). CW-161 moves them to the machine install; until then apps still have the copies.
- This repo's root links into `agent-team/`, `mods/agent-gantt`, the marketplace and the status pane.
- Choosing the GitHub account and a `set up this repo` command.

## Calls I made

- **This repo needs the machine install too.** Skills here will call `~/.collective-wisdom/scripts/`, so a Chief of Staff in this repo needs `./install-machine.sh` run once from the root checkout. Worktrees then run main's scripts and skills, not their branch's. The root links stay as they are. This is the one change to how development works here, and it matches the rule that only workflow on the merge target counts.
- **User-level skills win over an app's old copies.** Claude Code prefers a personal skill to a project skill of the same name, so once the machine install exists, an app still pinned to an older release runs the clone's skills. That is the ticket's goal (one release per machine), but an app's pin stops meaning anything before CW-161 removes it.
- **A separate `install-machine.sh`, not a mode of `install.sh`.** This keeps CW-160 out of `install.sh`, which CW-161 rewrites in parallel. The two tickets then share no file except, at worst, `README.md`, where CW-160 adds a new section and does not edit `## Install` or `## Update`.
- **`~/.collective-wisdom` links to the clone's `agent-team/` folder, not the clone root,** so call sites read `~/.collective-wisdom/scripts/gh.sh`, the same depth as `./scripts/gh.sh` today. Not `~/.agent-team`, which an app uses for its state folder.
- **Update is checkout plus rerun.** No update command. Checking out a newer tag in the clone updates every repo at once; the rerun only adds new skill links and drops dead ones. The script does not require a tag checkout, so the root checkout here (on `main`) can be the install.
- **Name conflicts are skipped, not overwritten.** A person's own `implementer` agent or `human-writing` skill wins, and the TODO names it.
- **Two Stop hooks in old apps.** An app with the old project-level hook runs both until someone removes it (CW-161 leaves existing settings alone). Both are read only and give the same answer, so the worst case is the rotation reason shown twice.
- **Cursor gets a printed instruction**, since its user rules have no file to write.
- **`install-machine.sh` joins the approval path**, because it writes into `~/.claude` like the files already on it. With `strict` tolerance this changes nothing today.

## Touches

none of: data, money, auth, user email, migrations. It writes outside the repo, under `$HOME` (`~/.claude`, `~/.agents`, `~/.cursor`, `~/.codex`, `~/.collective-wisdom`), so the security review checks those writes.
