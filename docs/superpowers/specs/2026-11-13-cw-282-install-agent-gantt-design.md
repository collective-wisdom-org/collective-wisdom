# CW-282: Install the agent-gantt plugin from install.sh

**Status:** Shipped
**Ticket:** [#282](https://github.com/collective-wisdom-org/collective-wisdom/issues/282)
**Shipped:** in PR #285, as specified

## Goal

`./install.sh` installs the Claude Code `agent-gantt` plugin at user scope, so a new machine with `claude` on PATH has the Gantt pane with no extra step. A rerun changes nothing, a machine without `claude` gets a to-do instead of a failure, and a dry run installs nothing.

## Today

Facts from `main` at `4f05a46`.

- `install.sh` `machine_install` links the skills and agents, merges the Stop hook into `~/.claude/settings.json`, merges the Cursor hooks (Chief of Staff rotation and `cursor_gantt_hook.ts`) into `~/.cursor/hooks.json`, then writes the instruction block and the Cursor rule. It keeps `MCHANGED` (changes made), `MTODOS` (steps left to the user, printed under `TODO:`) and `DRY` (`--dry-run`, every write skipped and status lines prefixed `[dry-run]` by `msay`). It never calls `claude`.
- `README.md` § Agent pane ends its first paragraph with "`install.sh` does not install it." and gives three manual routes: `/plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom` in a session, `claude plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom` in a shell, and the desktop app's Plugins menu.
- `AGENTS.md` § Product says the mod is one "that `install.sh` does not install", and its bullet on the mod says "People install the mod with `/plugin install`".
- `docs/agents/project.md` § Security overlays lists every path `install.sh` writes under `$HOME`. `~/.claude/plugins` is not on it.
- `.claude-plugin/marketplace.json` is named `collective-wisdom`, so the installed plugin's id is `agent-gantt@collective-wisdom`.
- The `claude` CLI (checked on this machine): `claude plugin list --json` prints a JSON array of installed plugins, each with `id` (like `agent-gantt@collective-wisdom`) and `scope`. `claude plugin install <name> --marketplace <source>` installs at user scope by default and adds the marketplace first when it is not added yet. `-y` is only needed for a command-source plugin, which `agent-gantt` is not.
- `agent-team/scripts/test_install_machine.py` runs `install.sh` in a throwaway clone with a temp `HOME` through one `install()` helper that passes the real `PATH`. On a machine with `claude` on PATH, once this change lands, every existing test would call the real `claude` against the temp `HOME`.

## Design

### The install step

A new step in `machine_install`, right after the Cursor hooks step:

1. No `claude` on PATH (`command -v claude` fails): add a to-do with the manual command, `claude plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom`, and the note that the desktop app installs it from its Plugins menu (README § Agent pane). Nothing else.
2. Ask `claude plugin list --json` and check, with `python3 -I`, for an entry whose `id` is `agent-gantt@collective-wisdom`. Found: print nothing, count nothing.
3. Not found, dry run: `msay "install  agent-gantt plugin (claude plugin install, user scope)"` and count one change, the way the other steps count what they would do.
4. Not found, real run: run `claude plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom --scope user`. Exit 0: `msay` the same line and count one change. Any other exit: add a to-do with the manual command and the last line of the command's output, and go on with the rest of the install.
5. `claude plugin list --json` itself fails or prints something that is not a JSON array: treat it as not installed and go to 3 or 4. A plugin that is installed already makes `claude plugin install` succeed or fail harmlessly, and a failure still only adds a to-do.

The step never ends the run: every failure becomes a to-do and `install.sh` still exits 0 at the end, as the other steps do.

### Tests

`test_install_machine.py`:

- The `install()` helper gets a PATH with a stub-bin folder first and every PATH folder that holds an executable `claude` dropped, so no test ever reaches a real `claude`. By default the stub folder holds a stub `claude` that reports `agent-gantt@collective-wisdom` as installed, so the existing tests (including "a rerun changes nothing") see no plugin change and keep their assertions.
- One table-driven test, `test_agent_gantt_plugin_install`, with the four cases the ticket names, each run once for real: no `claude` (the stub folder is empty), already installed, not installed (install exits 0) and install failure (install exits 1). The stub logs its arguments to a file. Each case checks the exit code (always 0), whether `install` was called, the `Done: N change(s)` count, and the to-do text.
- The dry-run case is one more row: not installed with `--dry-run`, `install` not called, the `[dry-run]` line printed.

### Docs

- `README.md` § Agent pane: replace "`install.sh` does not install it." with a sentence saying `./install.sh` installs it at user scope when `claude` is on PATH, and lists it under `TODO:` when not. Keep the three manual routes, introduced as the way to install it on a machine where `install.sh` skipped it or failed, and from the desktop app.
- `AGENTS.md` § Product: the mod "that `install.sh` installs with `claude plugin install`" instead of "does not install". The bullet "People install the mod with `/plugin install`" becomes "`install.sh` installs the mod with `claude plugin install`".
- `docs/agents/project.md` § Security overlays: add `~/.claude/plugins` (written by `claude plugin install`, which `install.sh` runs) to the list of paths `install.sh` writes.

## Calls I made

- **The marketplace source is GitHub, not the local clone.** `--marketplace collective-wisdom-org/collective-wisdom`, the same command the README gives. A local-path marketplace would also be named `collective-wisdom` and would clash with a machine that added the GitHub one by hand; it would also tie the plugin to whatever branch the clone has checked out.
- **"Installed" means any scope.** The check matches the id `agent-gantt@collective-wisdom` whatever its `scope`. Someone who installed it at project or local scope by hand gets no second, user-scope copy. The ticket says to install at user scope; this only decides what counts as already there.
- **A disabled plugin counts as installed.** `install.sh` does not re-enable a plugin the user turned off.
- **No timeout on the install.** macOS has no `timeout` by default, and the install is one network fetch. If it hangs, Ctrl-C stops `install.sh` after the earlier steps already ran; each is idempotent, so a rerun picks up.
- **A dry run counts the install as a change** and prints the line, like the other dry-run steps, but runs only `claude plugin list`, which reads and writes nothing of ours.
- **The existing tests get the stub too.** Without it they would call the real `claude` with a temp `HOME` and, on a dev machine, try a network install. The default stub says "installed", so their change counts stay as they are.
- **The to-do on failure quotes the last output line** of `claude plugin install`, so the user sees why without rerunning.

## Out of scope

- `status-pane`. It stays a separate marketplace install.
- Updating an installed plugin (`claude plugin update agent-gantt` stays manual).
- Installing the mod into apps.
- Cursor: it has no plugin of this kind; its gantt hooks are already installed.

## Acceptance

- A fresh machine with `claude` on PATH gets `agent-gantt` from `./install.sh` with no further step.
- A second `./install.sh` run reports no change for the plugin.
- Without `claude` on PATH, `./install.sh` exits 0 and prints the manual command as a to-do.
- A failed install exits 0, with a to-do.
- A dry run installs nothing.
- `README.md`, `AGENTS.md` and `docs/agents/project.md` no longer contradict the script.
- `shellcheck install.sh` and `python3 -I -m pytest -q agent-team/scripts` pass.
