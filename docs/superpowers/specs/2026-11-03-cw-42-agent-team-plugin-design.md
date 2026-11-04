# CW-42: Package the agent team as a Claude Code plugin

**Ticket:** [CW-42](https://github.com/dbeallor/collective-wisdom/issues/42)
**Status:** Draft

## Goal

The agent team ships as one Claude Code plugin, pinned to a release tag of this repo. It replaces copying files with `install.sh`. An app keeps only its own files: `docs/agents/project.md`, `AGENTS.md` and `.agent-team/state.json`. The skills, subagents, scripts, shared role docs and the Stop hook all come from the plugin.

The user asked for the replacement route: no generated duplicate copy, and no support for apps that keep copied files.

## Non-goals

- Moving any app to the plugin. Each app switches in its own install PR.
- Changing what the scripts or skills do, beyond how they find each other and the app.
- Keeping Cursor or Codex working. They found skills through copied `.claude/skills` and `.agents/skills`, and those copies go away (see Hosts).
- Pushing the first release tag. The approver pushes `v0.1.0` after merge (see Versions).

## Today

Facts from `main` at `e835684`.

- `install.sh` copies `agent-team/.claude/skills`, `.claude/agents`, `scripts` and `docs/agents` into the app. It seeds `project.md`, `AGENTS.md` and `docs/superpowers/README.md`, links `.agents/skills`, adds `.gitignore` lines, copies `.claude/settings.json` (the Stop hook) when the app has none, and writes `docs/agents/installed-from.txt` (`collective-wisdom <SHA>`).
- This repo runs its own Chief of Staff through root links into `agent-team/` (`.claude/skills`, `.claude/agents`, `.claude/settings.json`, `scripts`, `.agents/skills`, `docs/superpowers/README.md`, each shared entry of `docs/agents/`). `test_root_links.py` and `test_symlinked_root.py` check that layout.
- Skills, subagents and role docs call scripts as `python3 scripts/<name>.py`, `./scripts/gh.sh`, `./scripts/wait-for-ci.sh`, and once as `<root checkout>/scripts/merge_pr.py`. `docs/agents/trackers/github.md` alone has 34 `./scripts/gh.sh` calls.
- Skills send the model to shared role docs by repo path (`docs/agents/implementer.md`) and to subagents by bare name (`subagent_type: "implementer"`).
- Every script finds the app from its own location: `Path(__file__).absolute().parent.parent`. `wait-for-ci.sh` does `cd "$(dirname "$0")/.."`, then calls `./scripts/gh.sh`, so `gh` infers the repo from that folder.
- `ship-loop` § Team mode says workflow files change through a collective-wisdom PR "followed by an install PR in the app that bumps `docs/agents/installed-from.txt`".

What the Claude Code docs say (plugins reference, skills, marketplace reference, read 2026-11-03):

- A plugin is a folder with `.claude-plugin/plugin.json`, `skills/<name>/SKILL.md`, `agents/`, `hooks/hooks.json` and an optional `bin/`. Files in `bin/` are on the Bash tool's `PATH` while the plugin is enabled.
- `${CLAUDE_PLUGIN_ROOT}` is substituted in skill and agent Markdown bodies and in hook commands. It is not in the environment of commands Claude runs through the Bash tool, and nothing is substituted in other files Claude reads, such as role docs.
- Plugin skills load as `/<plugin>:<skill>`. The docs say a plugin skill and a project skill with the same short name both load. Nobody has checked this here.
- A marketplace (`.claude-plugin/marketplace.json`) lists plugins by `source`. An app adds the marketplace in `.claude/settings.json` under `extraKnownMarketplaces`, with a `github` source and a `ref` (a branch or tag), and turns the plugin on with `enabledPlugins`. A plugin enabled only in project settings is fetched on a new machine only when its marketplace entry uses a relative-path source.
- `version` in `plugin.json` is how Claude Code detects an update. Auto-update is off by default for third-party marketplaces.

## Design

### 1. `agent-team/` becomes the plugin

The folder is restructured in place into the plugin layout. Nothing is generated or duplicated.

```
.claude-plugin/marketplace.json     marketplace "collective-wisdom", one plugin "agent-team", source "./agent-team"
agent-team/
  .claude-plugin/plugin.json        name "agent-team", description, version
  skills/<name>/...                 was agent-team/.claude/skills
  agents/*.md                       was agent-team/.claude/agents
  hooks/hooks.json                  was agent-team/.claude/settings.json
  bin/                              one wrapper per script, plus agent-team-root
  scripts/                          as today
  docs/agents/                      shared role docs, as today
  docs/superpowers/README.md        as today (seeded into apps)
  templates/                        as today
```

`project.md` stays at `docs/agents/project.md` in this repo, outside `agent-team/`, and a test keeps it out of the plugin.

The script tests stay in `agent-team/scripts/` and ship inside the plugin unused. Moving them out would change the test command in `project.md` and CI for no gain.

### 2. How skills and docs call scripts

The plugin's `bin/` puts every script on `PATH`, so skills, subagents and role docs all call scripts by bare name. One rule covers all three, and it matters most for the role docs, which get no `${CLAUDE_PLUGIN_ROOT}` substitution.

| Today | After |
|---|---|
| `python3 scripts/<name>.py`, `./scripts/<name>`, `scripts/<name>` | `<name>` (for example `cos_state.py`, `gh.sh`, `wait-for-ci.sh`) |
| `<root checkout>/scripts/merge_pr.py` | `cd <root checkout> && merge_pr.py` |
| `docs/agents/<shared doc>` in skills and subagents | `${CLAUDE_PLUGIN_ROOT}/docs/agents/<shared doc>` |
| `docs/agents/<shared doc>` in role docs and `templates/AGENTS.md` | `$(agent-team-root)/docs/agents/<shared doc>` |
| `subagent_type: "<agent>"` | `subagent_type: "agent-team:<agent>"` |
| the subagent fallback "start a general subagent with `Read docs/agents/<role>.md`" | the same with the `${CLAUDE_PLUGIN_ROOT}` path |

The app's own paths (`docs/agents/project.md`, `docs/superpowers/...`, `.agent-team/state.json`) don't change.

Each `bin/<name>` is a two-line shell wrapper: `exec python3 "$(dirname "$0")/../scripts/<name>" "$@"` for a `.py` script, `exec "$(dirname "$0")/../scripts/<name>" "$@"` for a `.sh` one. `bin/agent-team-root` prints the plugin's root folder, so a doc or a person can find the role docs from a shell. Wrappers, not symlinks, because the docs don't say how symlinks survive the copy into the plugin cache.

`hooks/hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "cd \"$CLAUDE_PROJECT_DIR\" && python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/cos_rotation_check.py\" --hook || true" } ] }
    ]
  }
}
```

### 3. Scripts find the app from the working repo

New module `agent-team/scripts/app_root.py` with one function, `root()`: `git rev-parse --show-toplevel` run in the current directory, or the current directory if that fails. Every `ROOT`, `DEFAULT`, `DEFAULT_FILE`, `DEFAULT_STATE`, `INDEX` and `NOTES` built from `__file__` today uses it instead, including `project_config.DEFAULT` and `agent_usage.project_name`. Scripts call `gh.sh` from their own folder (`Path(__file__).parent / "gh.sh"`), as `cos_brief.py` does already. The `PROJECT_MD` and `COS_STATE_FILE` overrides keep working.

`wait-for-ci.sh` does the same in shell: `cd "$(git rev-parse --show-toplevel)"`, then calls `gh.sh` from its own folder.

This matches today for every caller that runs from the repo top: the root checkout gets the root checkout, and a worktree gets the worktree. `merge_pr.py` used to find the root checkout from its absolute path, so the merge-pr skill now runs it from the root checkout. The rule that the PR can't supply its own merge gate still holds, because the script comes from the pinned plugin, not from the PR's worktree.

### 4. Versions

- `agent-team/.claude-plugin/plugin.json` starts at `"version": "0.1.0"`. A release is a PR that bumps the version, then a tag `v<version>` on its merge commit, pushed by the approver. Tags are never moved.
- An app pins the plugin by pinning the marketplace to a tag in its `.claude/settings.json`:

  ```json
  {
    "extraKnownMarketplaces": {
      "collective-wisdom": {
        "source": { "source": "github", "repo": "dbeallor/collective-wisdom", "ref": "v0.1.0" }
      }
    },
    "enabledPlugins": { "agent-team@collective-wisdom": true }
  }
  ```

  The plugin's relative-path source means it comes from the same tagged checkout as the marketplace file, and that Claude Code fetches it from project settings alone.
- To move to a newer version, the app's install PR changes `ref` to the new tag.
- `docs/agents/installed-from.txt` is retired. The `ref` tag is the pin. The `ship-loop` workflow-files rule changes to "an install PR in the app that moves the plugin `ref` in `.claude/settings.json`".

### 5. `install.sh` becomes a setup script

It stops copying team files. What it still does, from a checkout of this repo at a release tag:

- Refuses unless this checkout is clean and `HEAD` is exactly a `v*` tag, and the target is a git repo with no uncommitted changes in the paths it touches (both as today, with the tag check in place of the commit pin).
- Seeds `docs/agents/project.md`, `AGENTS.md` and `docs/superpowers/README.md` when missing, and adds missing `.gitignore` lines (as today).
- Writes the two settings keys above into `.claude/settings.json`, with `ref` set to the tag it runs from. It creates the file if missing and edits only those two keys if not (with `python3`, which the team already needs). This replaces the old "merge the hook by hand" TODO.
- Lists, as TODOs, the old copies a pre-plugin install left behind: each shipped skill under `.claude/skills/`, each shipped agent under `.claude/agents/`, each shipped script under `scripts/`, each shared doc under `docs/agents/`, `.agents/skills`, `docs/agents/installed-from.txt`, and the old Stop hook entry in `settings.json`. It never deletes, as today; the app's install PR removes them.
- `--dry-run` keeps working.

### 6. This repo

This repo uses the plugin like any app:

- The root links for `.claude/skills`, `.claude/agents`, `.claude/settings.json`, `scripts` and `.agents/skills`, and the shared entries of `docs/agents/`, are removed. `docs/agents/project.md` stays. `docs/superpowers/README.md` stays a link to `agent-team/docs/superpowers/README.md`.
- The root `.claude/settings.json` becomes a real file that pins the marketplace to `v0.1.0`.
- To try a change before it is released, run `claude --plugin-dir agent-team` in the worktree.
- Order after merge: the approver pushes `v0.1.0`, then restarts the Chief of Staff. Until then this repo's team has no skills. This PR itself merges with the old skills on `main`.
- `AGENTS.md` (this repo's prose) is updated: edit under `agent-team/` and there are no root links; `gh.sh` instead of `./scripts/gh.sh`.
- CI's `shellcheck` step and the `Lint` row in `project.md` add `agent-team/bin/*`.

### 7. Hosts

The plugin covers Claude Code only. Cursor and Codex lose the team: they found skills through copied `.claude/skills` and `.agents/skills`, and nothing copies them now. `README.md` and `agent-team/docs/agents/README.md` say this plainly. The T3 Code requirement doesn't change; T3 runs Claude Code threads.

### 8. Same-name skill test

During the build, before `MERGE READY`, run `claude -p --plugin-dir agent-team` in a throwaway git repo that has its own `.claude/skills/ship-loop/SKILL.md` with a marker line. This is the state of an app mid-switch, with old copies still present. Record in the PR body and the as-built: whether both skills load, which one `/ship-loop` runs, and which one the model picks when told "use the ship-loop skill". The same run checks that `bin/` is on `PATH` in a subagent's Bash and that `${CLAUDE_PLUGIN_ROOT}` is substituted in an agent body. If `bin/` is not on `PATH` in subagents, skills and subagents call `${CLAUDE_PLUGIN_ROOT}/bin/<name>` instead, and the PR says so.

## Tests

Per `AGENTS.md` § Testing, one table-driven test per rule:

- `test_app_root.py` replaces `test_symlinked_root.py`. It copies `agent-team/` to a temp plugin folder and makes a temp app repo with a fixture `project.md`. For each script with a root lookup, it runs it from the app top and from a subfolder, and checks it names the app's `project.md` and `.agent-team/state.json`. It also runs every script through its `bin/` wrapper with `--help` and checks for no import error. This covers the ticket's "scripts finding the app root when run from the plugin path".
- `test_root_links.py` is rewritten for the new layout: no dangling links, `docs/agents/project.md` is a real file and nowhere under `agent-team/`, every script has a `bin/` wrapper, the hook command names a script that exists, and no skill, agent or role doc still calls a script by `scripts/` path.
- `install.sh` gets one table-driven test over a temp app: fresh app, app with its own `settings.json`, app with old copied files, and a checkout not at a tag. Check the settings keys, the TODO list and the refusal.
- Once by hand (not in CI): in a temp app with only the plugin enabled through `--plugin-dir`, run a skill, `cos_state.py` through `bin/` and the Stop hook, and check the app's `.agent-team/state.json` was written. Record it in the PR.

## Calls I made

- **Cursor and Codex lose the team.** The replacement route removes the copied skills they read. Keeping them would mean copying files again.
- **This repo's own Chief of Staff runs on the pinned plugin too, so it has no skills from merge until `v0.1.0` is pushed.** After that, a change to the team takes effect here only when a release is tagged. `claude --plugin-dir agent-team` tries a change before that.
- **`install.sh` stays, as a setup script**: it seeds the app's own files and writes the pinned settings. It never deletes old copies; it lists them for the app's install PR.
- **Scripts on `PATH` through `bin/`, called by bare name.** The role docs get no `${CLAUDE_PLUGIN_ROOT}` substitution. Skills fall back to `${CLAUDE_PLUGIN_ROOT}/bin/` if `bin/` isn't on `PATH` in subagents.
- **Pin by git tag on the marketplace (`ref: v0.1.0`), with the plugin as a relative-path source.** The marketplace `ref` takes a branch or tag, not a SHA. A tag pins the marketplace file and the plugin together, and the relative path lets project settings fetch the plugin on a new machine.
- **`installed-from.txt` is retired** in favor of the `ref` tag.
- **Version 0.1.0, tags `v<version>`, pushed by the approver after merge.** This PR pushes no tag.
- **Scripts find the app with `git rev-parse --show-toplevel` in the current directory**, so `merge_pr.py` is now run from the root checkout (`cd <root checkout> && merge_pr.py`).
- **Script tests stay in `agent-team/scripts/` and ship inside the plugin unused.**
- **Subagent types become `agent-team:<name>`.** Skill-to-skill mentions ("invoke `open-pr`") stay as they are; the model finds `agent-team:open-pr`.
- **Names: plugin `agent-team`, marketplace `collective-wisdom`.**

## Risks

- `bin/` on `PATH` and `${CLAUDE_PLUGIN_ROOT}` substitution are checked only by the manual run, not CI.
- An app mid-switch has two copies of each skill until its install PR deletes the old ones. The same-name test shows what that looks like.
- A bad release reaches an app only when it moves its `ref`, but this repo's own team breaks until a fixed tag is pushed.
