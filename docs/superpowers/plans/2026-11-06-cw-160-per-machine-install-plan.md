# CW-160 plan: install the agent team once per machine

Spec: [design](../specs/2026-11-06-cw-160-per-machine-install-design.md). Shared files are edited under `agent-team/`; `install.sh`, `README.md` and `CONTRIBUTING.md` sit at the root. The app-target forms of `install.sh` (and `test_install.py`, `agent-team-update.sh`, `agent-team/.claude/settings.json`, `templates/gitignore`) stay as they are: CW-161 changes them.

## Tasks

Three write scopes, disjoint, so they run in parallel.

### A. Machine mode of install.sh (scope: `install.sh`, `agent-team/templates/machine-instruction.md`, `agent-team/scripts/test_install_machine.py`, `README.md`)

1. `agent-team/templates/machine-instruction.md`: the instruction text (a repo with no `docs/agents/project.md` is not running the team; don't start team skills or run team scripts there). Short, plain, no em dashes.
2. `install.sh`: with no target path and none of `--update`, `--check`, `--to`, `--from`, `--force`, run the machine install and exit; `--dry-run` alone is allowed. Everything else keeps today's code path byte for byte (the `[ -n "$TARGET" ] || usage` check becomes the dispatch). The machine install, per spec § Builds 1: refuses a clone that is not its own git root or is a linked worktree; links `~/.collective-wisdom` to `<clone>/agent-team`; per-skill links into `~/.claude/skills`, `~/.agents/skills`, `~/.cursor/skills`; per-agent links into `~/.claude/agents`; never replaces a real file or a foreign link (lists it under `TODO:`); removes only its own dangling links (pointing into this clone); merges the Stop hook (`python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true`) into `~/.claude/settings.json` as JSON (inline python3, temp file and rename, skip when a hook command already mentions `cos_rotation_check.py`, leave an invalid file alone and TODO it); replaces the block between `<!-- collective-wisdom:begin -->` and `<!-- collective-wisdom:end -->` in `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`; prints the text under `TODO:` for Cursor; `--dry-run` writes nothing; ends with `installed collective-wisdom <sha> [<tag>] from <clone>`. Writes only under `$HOME`. Passes `shellcheck install.sh`.
3. `test_install_machine.py`: table-driven, `HOME` set to a temp folder and a temp git clone fixture (a copy of `install.sh` plus a tiny `agent-team/`): fresh install links everything and adds the hook; a rerun changes nothing; an existing settings file keeps its keys; a real folder and a foreign link of a shipped name are kept and listed; a dangling link into the clone is removed and a dangling foreign link is kept; the instruction block is replaced, not duplicated; a linked worktree is refused; `--dry-run` writes nothing. Test lines should not exceed the feature lines.
4. `README.md`: a `## Install on a machine` section before `## Install` (install, update by checking out a newer release in the clone and rerunning `./install.sh`, what it links, the TODO cases). Say `## Install` and `## Update` describe the older copy-into-an-app route until CW-161 removes it. Do not edit those two sections. In "Running a Chief of Staff in this repo" say to run `./install.sh` from the root checkout. Add the machine mode to the `Layout` bullet for `install.sh`.

### B. Call sites (scope: every `.md` under `agent-team/.claude/skills/`, `agent-team/docs/agents/`, `agent-team/templates/` except `machine-instruction.md`, plus `agent-team/scripts/test_call_sites.py`)

1. Replace every instruction to run a script, `./scripts/<name>` and bare `scripts/<name>.py|.sh`, with `~/.collective-wisdom/scripts/<name>`. Keep prose that names the `scripts/` folder as a place (the approval path list, "a PR that touches any script"). Leave `docs/superpowers/` alone.
2. `test_call_sites.py`: one test that no `.md` file under those three folders contains `./scripts/<name>` or a bare `scripts/<name>.(py|sh)` call outside `~/.collective-wisdom/`.
3. Run the whole suite: `test_section_pointers.py` and `test_tracker_docs.py` read these files.

### C. Scripts (scope: `agent-team/scripts/*.py` and `*.sh` other than `test_*` and `agent-team-update.sh`; plus `test_cos_rotation_check.py`)

1. `cos_rotation_check.py`: `--hook` exits 0 silently, before any other read, when the app root has no `docs/agents/project.md`. `skill_paths()` and `skill_commit()` resolve `SKILL_PATHS` against the folder above `HERE` (the clone's `agent-team/`), and run `git log` in that folder's repo (this works through `~/.collective-wisdom`); `branch()` still reads the app. Keep the existing symlink, subfolder and missing-path behavior.
2. Usage strings that scripts print (`scripts/foo.py ...` in error lines) and docstring usage lines name `~/.collective-wisdom/scripts/foo.py`. Change nothing else about what a script does. Update any test that pins the old strings.
3. Tests in `test_cos_rotation_check.py`: the hook is silent in a repo with no `project.md`; the skill commit follows the clone's history and holds with the clone outside the app repo.

## Verify

```
python3 -I -m pytest -q agent-team/scripts
shellcheck install.sh tag-release.sh agent-team/scripts/*.sh
```

Plus a manual run: `HOME=$(mktemp -d) ./install.sh --dry-run`, then without `--dry-run`, then again (the second run reports no changes).
