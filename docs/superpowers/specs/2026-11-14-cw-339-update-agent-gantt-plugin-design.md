# CW-339: Update the agent-gantt plugin when install.sh finds an older version

**Status:** Draft
**Ticket:** [#339](https://github.com/collective-wisdom-org/collective-wisdom/issues/339)

## Goal

Rerunning `./install.sh` after a PR bumped the mod's version updates the installed agent-gantt plugin, says a restart of Claude Code is needed, and never stops the rest of the run when the update can't happen.

## Today

Facts from `main` at `6e85821`.

- `install.sh` (the agent-gantt block, about lines 285-305) runs `claude plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom --scope user` only when `claude plugin list --json` has no `agent-gantt@collective-wisdom` entry. An entry at any scope, enabled or not, counts as installed, and then nothing happens.
- `mods/agent-gantt/.claude-plugin/plugin.json` has `"version": "0.1.12"`.
- On this machine (`claude` 2.1.325) the list entry is `{"id": "agent-gantt@collective-wisdom", "version": "0.1.12", "scope": "user", "enabled": true, "installPath": ..., "readFromFolder": ".../mods/agent-gantt", "folderVersion": "0.1.12", ...}`.
- `claude plugin update [options] <plugin>` takes `-s, --scope <scope>` and says "restart required to apply".
- README § Agent pane says "Update with `claude plugin update agent-gantt`", and README § install's TODO list names the two plugin to-dos (no `claude`, install failed).
- `agent-team/scripts/test_install_machine.py` has `GANTT_PLUGIN`, a table over a `claude` stub with modes `installed`, `ok`, `fail` and `missing`. The stub logs every call to `claude.log`.

## Design

1. **Read both versions.** When the list has an `agent-gantt@collective-wisdom` entry, the existing Python check also prints the `version` of the entry whose `scope` is `user`, or nothing when there is no user-scope entry or its `version` is not a string. The clone's version is `version` in `$ROOT/mods/agent-gantt/.claude-plugin/plugin.json`.
2. **Compare.** A version reads only when it is dot-separated non-negative integers (`0.1.12`, `1.0`); it compares part by part as numbers, with missing parts as 0 (`1.0` equals `1.0.0`). The compare runs in the same `python3 -I` call so bash does no version parsing.
3. **Act on the result.**
   - Installed older than the clone: run `claude plugin update agent-gantt --scope user` (stdin from `/dev/null`, output captured, as the install does). On success print `update  agent-gantt plugin <old> -> <new> (claude plugin update, user scope; restart Claude Code to apply)` and count one change. In a dry run print the same line with the `[dry-run]` prefix `msay` adds, count the change, and don't run it.
   - On a failed update, add the to-do `Update the agent-gantt plugin (the Gantt pane) by hand: claude plugin update agent-gantt --scope user (it failed: <last line of output>)`, or `(it failed)` with no output, the same shape as the install to-do. The run goes on.
   - Installed equal or newer, no user-scope entry, or an installed version that does not read: leave it alone. No line, no change, no to-do.
   - The clone's version does not read (file missing, not JSON, no `version`, or not dotted integers) while a user-scope entry has a version: add the to-do `Check the agent-gantt plugin version by hand: mods/agent-gantt/.claude-plugin/plugin.json in <clone> has no readable version, so install.sh could not tell if  claude plugin update agent-gantt --scope user  is needed.` The run goes on.
   - `claude` not on PATH: unchanged (the install to-do already gives the command, and the user can't be behind on a plugin they can't list).
   - Not installed: unchanged (install as today).
4. **Restart line.** After a real or dry-run update, the summary after `Done: ...` (before `TODO:`) adds `Restart Claude Code to load the updated agent-gantt plugin.` A run with no update prints nothing new.
5. **Docs.** README § Agent pane: `./install.sh` installs the plugin and, when the installed version is older than the clone's, updates it (restart Claude Code to apply); the "Update with" line says `install.sh` does this and `claude plugin update agent-gantt --scope user` does it by hand. README § install: the paragraph that names the plugin install also names the update, and the TODO list gets two bullets: a failed update (command and last line of output) and an unreadable clone version.
6. **Test.** Extend `GANTT_PLUGIN` in `test_install_machine.py`. The stub's list output takes an installed version, its `plugin update` branch exits 0 or fails like the `fail` mode, and the test writes `mods/agent-gantt/.claude-plugin/plugin.json` with `0.1.12` into the `world` clone (the fixture has none today, so the existing rows, whose stub lists no version, still change nothing). New rows: older (update called, 1 change, restart line), same (nothing), newer (nothing), installed version unreadable (nothing), project-scope entry only (nothing), update fails (to-do with the last output line, run exits 0), dry run older (line printed, 1 change, update not called), clone version unreadable (to-do, update not called). A new column asserts whether `plugin update agent-gantt --scope user` was called. Existing rows keep their meaning.

## Leaves out

- Updating from a session start hook or on a timer, bumping the version automatically in a PR, or any plugin other than agent-gantt (ticket's Out of scope).
- Updating a project- or local-scope install: `install.sh` installs at user scope only, so it updates only that one.
- Checking that the update reached the clone's version afterwards. `claude plugin update` fetches from the marketplace, which is GitHub `main`, not the clone; when the clone is ahead of `main` the update may land an older version. The summary reports the versions it compared, not the result.
- Pre-release or build suffixes (`0.2.0-beta`): they don't read, so the plugin is left alone. The mod has never used them.
- Using `folderVersion` or `readFromFolder`: seen on one `claude` version only, and `version` is the installed one.

## Calls I made (surprising first)

- **The update fetches from the marketplace, not the clone.** The compare uses the clone's version to decide, but `claude plugin update` takes whatever the marketplace has. On a machine whose clone tracks `main` they match; a clone ahead of `main` may update to a version still older than the clone's, and the next run tries again. I didn't add a post-update check (Leaves out).
- **"Unreadable version" splits two ways.** The ticket lists it both as a to-do and as left alone. An unreadable installed version is left alone (the ticket's Scope line says so); an unreadable clone version is a to-do, because that is our own file and something is wrong with the clone.
- **Only a user-scope entry is compared.** A project-scope-only entry counts as installed, as today, and is left alone, since `--scope user` would fail on it.
- **The restart line sits after the Done count, not under TODO**, so a run that updated cleanly still lists no to-do.
- **A dry run counts the update as a change** and prints it, matching how a dry run counts the install today.
- **Versions compare as dotted integers with missing parts as 0**; anything else doesn't read.

Touches: none of these (data, money, auth, user email, migrations).
