# CW-161 plan: leave only project.md in a consuming repo

Spec: [design](../specs/2026-11-06-cw-161-project-md-only-design.md). Shared files are edited under `agent-team/`; `install.sh`, `README.md` and `AGENTS.md` sit at the root. This builds on CW-160's machine install and starts only after it has merged.

## Tasks

Four write scopes, disjoint, so they run in parallel.

### A. install.sh (scope: `install.sh`, `agent-team/scripts/test_install.py`, `agent-team/scripts/test_install_machine.py`, `agent-team/scripts/agent-team-update.sh`)

1. `install.sh`: delete the app-target code (the target path, `--update`, `--check`, `--to`, `--from`, `--force`, the pin, `extract`, `shipped`, `drift`, `sync_dir`, `seed_file`, the dirty check, the seeding, the `.agents/skills` link and the `.gitignore` append). A target path or an app-target flag exits 2 with a message that points to the machine install and the removal command, and writes nothing. The machine mode stays as CW-160 merged it.
2. Delete `agent-team/scripts/agent-team-update.sh`.
3. `test_install.py`: drop the app-target cases, keep `test_tag_release`. `test_install_machine.py`: one more row, a target path exits 2 and writes nothing.

### B. Removal command (scope: new `agent-team/scripts/remove_app_copies.py` and `agent-team/scripts/test_remove_app_copies.py`)

1. `remove_app_copies.py <app>` reads the pin, lists the shipped files with `git ls-tree` at the pinned commit in the machine clone, and removes the app's copies of them, the pin, the `.agents/skills` link and the copied mods. It leaves `project.md`, `AGENTS.md`, `settings.json`, `.gitignore` and any app-owned file untouched. A hand-edited copy stops it before any write unless `--force`. `--dry-run` writes nothing.
2. One table-driven test: no pin, a clean old app, app-owned files kept, a hand edit with and without `--force`, a dry run, a malformed pin, a pinned commit missing from the clone, a run inside collective-wisdom.

### C. Role docs from the machine install (scope: every `.md` under `agent-team/.claude/skills/`, `agent-team/.claude/agents/`, `agent-team/docs/agents/` and `agent-team/templates/` except `machine-instruction.md`; `agent-team/docs/superpowers/README.md`; `agent-team/scripts/test_call_sites.py`)

1. Every read of a shared role doc becomes `~/.collective-wisdom/docs/agents/<path>`. `docs/agents/project.md` and prose that names `docs/agents/` as a place stay.
2. `ship-loop` § Workflow files: shared files change in a PR here and reach every repo when the machine clone updates; no install PR, no `installed-from.txt`. Drop the same install-PR wording elsewhere in the skills and role docs.
3. `status-pane.md` says to install with `claude plugin install status-pane --marketplace collective-wisdom-org/collective-wisdom`. `docs/superpowers/README.md` drops the `install.sh --update <app>` line.
4. `test_call_sites.py` gains a second rule: no bare `docs/agents/<file>.md` or `docs/agents/trackers/...` other than `project.md`.

### D. Docs at the root (scope: `README.md`, `AGENTS.md`, `docs/agents/project.md`)

Delete the app-target `## Install`, `## Update` and check sections and the pin text; add `## Moving an app off the copied team`; say an app commits only `project.md`; install the status pane from the marketplace. `AGENTS.md` and `project.md` follow the new layout.

## Verify

```
python3 -I -m pytest -q agent-team/scripts
shellcheck install.sh tag-release.sh agent-team/scripts/*.sh
```

Plus a manual run of `remove_app_copies.py --dry-run`, then for real, on a scratch old-style app made with the previous release's `install.sh`: only the shipped copies go, `project.md`, `AGENTS.md`, `settings.json`, `.gitignore` and an app-owned skill are unchanged.
