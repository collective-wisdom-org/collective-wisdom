# CW-339: Update the agent-gantt plugin when install.sh finds an older version

**Status:** Shipped
**Shipped:** in PR #358, as specified
**Ticket:** [#339](https://github.com/collective-wisdom-org/collective-wisdom/issues/339)

## Goal

When the mod's version in the clone moves past the installed agent-gantt plugin, the plugin gets updated, by a rerun of `./install.sh` and also by a running Chief of Staff thread, which then starts a fresh session so it runs the new plugin. A failed update never stops `install.sh` or the Chief of Staff's turn.

The user's change on the first spec: "make sure an active cos thread also picks up changes and upgrades the plugin".

## Today

Facts from `main` at `6e85821`.

- `install.sh` (the agent-gantt block, about lines 285-305) runs `claude plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom --scope user` only when `claude plugin list --json` has no `agent-gantt@collective-wisdom` entry. An entry at any scope, enabled or not, counts as installed, and then nothing happens.
- `mods/agent-gantt/.claude-plugin/plugin.json` has `"version": "0.1.12"`.
- On this machine (`claude` 2.1.325) the list entry is `{"id": "agent-gantt@collective-wisdom", "version": "0.1.12", "scope": "user", "enabled": true, "installPath": ..., "readFromFolder": ".../mods/agent-gantt", "folderVersion": "0.1.12", ...}`. `claude plugin list --json` takes about 0.3 s. `claude plugin marketplace list` shows the `collective-wisdom` marketplace as `Source: Folder (<root checkout>)`, so here an update reads the root checkout, not GitHub.
- `claude plugin update [options] <plugin>` takes `-s, --scope <scope>` and says "restart required to apply". A plugin loads when a Claude Code session starts.
- `~/.collective-wisdom` links to `<root checkout>/agent-team`, and `merge_pr.py` fast-forwards the root checkout after each merge. So a merge changes the clone's mod version at once, while the running Chief of Staff session keeps the plugin it loaded.
- `cos_rotation_check.py` runs as the last Bash call of every Chief of Staff turn and from the Stop hook. Its skill-change trigger (`decide()`, `agent-team/scripts/cos_rotation_check.py:140`) compares `skillCommit` in state with the last commit touching `SKILL_PATHS` (the chief-of-staff and project-manager skills and the chief-of-staff role doc), and on a quiet turn on the merge target branch prints `rotate: skill changed ...`. `mods/` is not in `SKILL_PATHS`, so a PR that changes only the mod never resets the thread. On mode `none` (Cursor, Codex) nothing rotates.
- The reset (`rotation.md` § Thread rotation) sends the thread `CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over.` with `freshContext: true`; take over step 4 saves `skillCommit`.
- `cos_state.py` allows a fixed set of `top` keys (`agent-team/scripts/cos_state.py:83`) and checks `skillCommit`'s shape.
- README § Agent pane says "Update with `claude plugin update agent-gantt`", and README § install's TODO list names the two plugin to-dos (no `claude`, install failed).
- `agent-team/scripts/test_install_machine.py` has `GANTT_PLUGIN`, a table over a `claude` stub with modes `installed`, `ok`, `fail` and `missing`, which logs every call to `claude.log`.

## Design

### 1. One script that compares and updates: `gantt_plugin.py`

A new `agent-team/scripts/gantt_plugin.py` holds the compare and update, so `install.sh` and the Chief of Staff run the same code. It finds the clone from its own path (`scripts/` → `agent-team/` → its git top level) and reads the clone's version from `mods/agent-gantt/.claude-plugin/plugin.json`. It prints one line and exits 0, whatever happens:

| Case | Line |
|---|---|
| `claude` not on PATH | `gantt-plugin: no claude` |
| No `agent-gantt@collective-wisdom` entry, or the list fails or is not a JSON array | `gantt-plugin: not installed` |
| An entry but none at `scope: user`, or the user entry's `version` does not read | `gantt-plugin: left alone (<why>)` |
| Installed equal to or newer than the clone | `gantt-plugin: current <installed>` |
| The clone's version does not read | `gantt-plugin: todo Check the agent-gantt plugin version by hand: mods/agent-gantt/.claude-plugin/plugin.json in <clone> has no readable version, so it is unknown whether  claude plugin update agent-gantt --scope user  is needed.` |
| Installed older, `--dry-run` | `gantt-plugin: would update <old> -> <new>` |
| Installed older, update succeeds | `gantt-plugin: updated <old> -> <new>` |
| Installed older, update fails | `gantt-plugin: todo Update the agent-gantt plugin (the Gantt pane) by hand: claude plugin update agent-gantt --scope user (it failed: <last line of output>)`, or `(it failed)` with no output |

A version reads only when it is dot-separated non-negative integers (`0.1.12`, `1.0`); versions compare part by part as numbers, with missing parts as 0. The update runs `claude plugin update agent-gantt --scope user` with stdin from `/dev/null` and a 120 s timeout (a timeout is a failure). The script never installs: `install.sh` keeps its install step.

### 2. `install.sh`

The plugin block runs `python3 -I "$ROOT/agent-team/scripts/gantt_plugin.py"` (with `--dry-run` in a dry run) and acts on the line:

- `no claude`, `not installed`: as today (the to-do, or the install).
- `updated` / `would update`: print `update  agent-gantt plugin <old> -> <new> (claude plugin update, user scope)` and count one change. The summary after `Done: ...` (before `TODO:`) adds `Restart Claude Code to load the updated agent-gantt plugin.`
- `todo <text>`: add `<text>` to the to-dos. The run goes on.
- `current`, `left alone`, or any other line: nothing.

The inline Python that reads `claude plugin list` moves into the script.

### 3. The running Chief of Staff

A new state key, `ganttPluginVersion`: the agent-gantt version this Chief of Staff session runs. `cos_state.py` accepts a string of dot-separated integers or `null` for it, and rejects anything else.

- **Rotation trigger.** `cos_rotation_check.py` reads the clone's mod version (a file read; it never runs `claude`, so the Stop hook stays fast). When `ganttPluginVersion` is set, the clone's version reads and differs from it, and the branch is the merge target branch, it works like the skill change: on a quiet turn `rotate: agent-gantt plugin <old> -> <new>; mode <mode>`, otherwise `ok (plugin change waits: <why>)`. A skill change on the same turn wins the line. `null`, an unreadable stored value or an unreadable clone version turns the trigger off with no line of its own. On mode `none` it does nothing (the plugin is Claude Code only).
- **Update before the reset.** In `rotation.md`'s Reset, a new first step for every reset reason: run `python3 ~/.collective-wisdom/scripts/gantt_plugin.py`. On `todo <text>` add a Cleanup line `agent-gantt plugin: <text>`; the reset goes on whatever it prints. The fresh session that the reset starts then loads the updated plugin.
- **Take over.** Take over step 1 (and resume mode, which runs it) also runs `gantt_plugin.py`. Step 4 saves `ganttPluginVersion`: the `<installed>` from `current`, or the `<old>` from `updated <old> -> <new>` (this session loaded the old one, so the next quiet turn resets to load the new one, and that reset's pre-step finds it current), or `null` for any other line. A `todo` line becomes a Cleanup line, as in the reset.
- `state-keys.md` gets the `ganttPluginVersion` bullet, and `rotation.md`'s trigger table gets a Plugin change row.

So a merge that bumps the mod reaches a running Chief of Staff on its next quiet turn: the rotation check sees the clone's new version, the reset updates the plugin, and the take-over records the new version. Child threads start new sessions, so any child started after the update loads the new plugin.

### 4. Docs

- README § Agent pane: `./install.sh` installs the plugin and updates it when the installed version is older than the clone's (restart Claude Code to apply), and a running Chief of Staff updates it after a merge that bumps the mod and resets itself to load it. The "Update with" line says `claude plugin update agent-gantt --scope user` does it by hand.
- README § install: the paragraph naming the plugin install also names the update, and the TODO list gets two bullets: a failed update (command and last line of output) and an unreadable clone version.
- The `cos_rotation_check.py` docstring names the new lines.

### 5. Tests

- `test_gantt_plugin.py`, one table over a `claude` stub (list output, update exit code and output): older (update called, `updated`), same, newer, installed version unreadable, project-scope entry only, not installed, no `claude`, update fails (`todo` with the last output line), dry run older (`would update`, update not called), clone version unreadable (`todo`, update not called). Each row checks the line and whether `plugin update agent-gantt --scope user` was called.
- `GANTT_PLUGIN` in `test_install_machine.py` gains two rows (older: 1 change, update line and restart line; update fails: the to-do, exit 0). The `world` fixture copies `gantt_plugin.py` and writes a plugin.json. The existing rows keep their meaning.
- `test_decide` in `test_cos_rotation_check.py` gains rows: plugin changed on a quiet turn rotates, on a busy turn waits, a skill change on the same turn wins, `null` or a clone version that does not read prints the ordinary line, mode `none` never rotates on it.
- `test_cos_state.py`'s `top` table gains `ganttPluginVersion` rows (`0.1.12` and `null` accepted, `v1`, `1.x` and a number rejected).

## Leaves out

- Updating from a session start hook or on a timer, bumping the version automatically in a PR, or any plugin other than agent-gantt (ticket's Out of scope).
- Updating a project- or local-scope install: `install.sh` installs at user scope only, so only that one is updated.
- Rerunning all of `install.sh` from the Chief of Staff, for example to link a new skill name after a merge. Only the plugin is updated.
- Restarting child threads that are already running: they keep the plugin they loaded until they end.
- Checking after the update that the installed version reached the clone's.
- Pre-release or build suffixes (`0.2.0-beta`): they don't read, so the plugin is left alone. The mod has never used them.
- Cursor and Codex Chief of Staff threads: they don't run Claude Code plugins and don't reset.

## Calls I made (surprising first)

- **A running Chief of Staff resets its own context to load the new plugin.** A plugin loads at session start, so updating it in place leaves the running session on the old one. I reuse the skill-change reset (the same quiet-turn rule), and the update runs just before the reset sends its message. I have not seen a `freshContext: true` reset load a newly updated plugin; the build checks it on this machine, and the PR lists it under Not proven if it can't.
- **The Stop hook never runs `claude`.** The rotation check only reads the clone's plugin.json and compares it with state; `claude plugin list` and the update run in the reset and the take over, which happen at most once per reset.
- **A take-over that had to update records the old version**, so the next quiet turn resets once more to load the new one. This covers `start the team` and resume, which don't go through the reset's pre-step.
- **The update source is the marketplace.** On this machine the marketplace is the root checkout folder, so the update lands the clone's version. On a machine whose marketplace is GitHub, an update from a clone ahead of `main` can land an older version; the next check tries again. No check runs afterwards.
- **"Unreadable version" splits two ways.** The ticket lists it both as a to-do and as left alone. An unreadable installed version is left alone (the ticket's Scope line says so); an unreadable clone version is a to-do, because that file is ours.
- **Only a user-scope entry is compared.** A project-scope-only entry still counts as installed and is left alone, since `--scope user` would fail on it.
- **The restart line in `install.sh` goes after the Done count, not under TODO**, so a clean update shows no to-do. A dry run counts the update as a change, as it counts the install today.
- **Versions compare as dotted integers with missing parts as 0**; anything else doesn't read.

Touches: none of these (data, money, auth, user email, migrations). It changes `install.sh`, the chief-of-staff skill, `cos_rotation_check.py` and `cos_state.py`, which are on the approval and hands paths.
