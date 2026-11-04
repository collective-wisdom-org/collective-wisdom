# CW-42: Package the agent team as a Claude Code plugin

**Ticket:** [CW-42](https://github.com/dbeallor/collective-wisdom/issues/42)
**Status:** Draft

## Goal

A Claude Code app can run the agent team from a plugin pinned to one version of this repo, instead of from files `install.sh` copied into it. The skills, the subagents, the `cos_*.py` scripts and the Stop hook come from the plugin; the app keeps only its own `docs/agents/project.md` and `.agent-team/state.json`.

## Non-goals

- Moving any app to the plugin. Each app switches in its own install PR.
- Changing what the scripts or skills do.
- Changing `install.sh`. It stays the install path for Cursor and Codex, and for Claude Code apps that don't switch.
- Cutting the first release tag. That happens after this PR merges (see Versions).

## Today

Facts from `main` at `e835684`.

- `install.sh` copies `agent-team/.claude/skills`, `.claude/agents`, `scripts` and `docs/agents` into the app, seeds `project.md` and `AGENTS.md`, links `.agents/skills`, and writes `docs/agents/installed-from.txt` (`collective-wisdom <SHA>`).
- The Stop hook in `agent-team/.claude/settings.json` runs `python3 "$CLAUDE_PROJECT_DIR/scripts/cos_rotation_check.py" --hook || true`.
- Skills and agents call scripts as `python3 scripts/<name>.py`, `./scripts/gh.sh`, `./scripts/wait-for-ci.sh`, and once as `<root checkout>/scripts/merge_pr.py`. The shared docs do too: `docs/agents/trackers/github.md` alone has 34 `./scripts/gh.sh` calls.
- Skills point at shared role docs by repo path (`docs/agents/implementer.md`, `docs/agents/trackers/README.md`) and at subagents by bare name (`subagent_type: "implementer"`).
- Every script finds the app from its own location: `Path(__file__).absolute().parent.parent`. `wait-for-ci.sh` does `cd "$(dirname "$0")/.."` and then calls `./scripts/gh.sh`, so `gh` infers the repo from that folder.

What the Claude Code docs say (plugins reference, skills, marketplace reference, read 2026-11-03):

- A plugin is a folder with `.claude-plugin/plugin.json`, `skills/<name>/SKILL.md`, `agents/`, `hooks/hooks.json` and an optional `bin/`. Files in `bin/` are on the Bash tool's `PATH` while the plugin is enabled.
- `${CLAUDE_PLUGIN_ROOT}` is substituted in skill and agent Markdown bodies and in hook commands. It is not in the environment of commands Claude runs through the Bash tool, and it is not substituted in other files Claude reads (role docs).
- Plugin skills load as `/<plugin>:<skill>`. The docs say a plugin skill and a project skill with the same short name both load. Nobody has checked this here.
- A marketplace (`.claude-plugin/marketplace.json`) lists plugins by `source`. An app adds it in `.claude/settings.json` under `extraKnownMarketplaces` with a `github` source and a `ref` (branch or tag), and turns the plugin on with `enabledPlugins`. A plugin enabled only in project settings is fetched on a new machine only when its marketplace entry uses a relative-path source.
- `version` in `plugin.json` is how Claude Code detects an update. Auto-update is off by default for third-party marketplaces.

## Design

### 1. Layout

Two new things at the repo root:

- `.claude-plugin/marketplace.json`: marketplace `collective-wisdom`, owner `dbeallor`, one plugin `agent-team` with `"source": "./plugin/agent-team"`.
- `plugin/agent-team/`: the plugin, built from `agent-team/` by a script.

```
plugin/agent-team/
  .claude-plugin/plugin.json   hand-written: name, description, version
  skills/<name>/...            from agent-team/.claude/skills, paths rewritten
  agents/*.md                  from agent-team/.claude/agents, paths rewritten
  docs/agents/...              from agent-team/docs/agents, paths rewritten
  scripts/*                    from agent-team/scripts, minus test_*.py and conftest.py
  bin/<script name>            one small wrapper per script
  hooks/hooks.json             the Stop hook
```

`agent-team/` stays the only place anyone edits. `plugin/agent-team/` is generated and committed, because a pinned tag has to contain the plugin as files. `project.md` and `templates/` are never copied.

### 2. The build script

`build_plugin.py` at the repo root, next to `install.sh` (it is a tool for this repo, so it does not ship to apps). It deletes everything in `plugin/agent-team/` except `.claude-plugin/plugin.json`, copies the files above, and applies these rewrites to every `.md` file it copies:

| In `agent-team/` | In the plugin |
|---|---|
| `python3 scripts/<name>.py`, `./scripts/<name>`, `scripts/<name>` | `<name>` (a command on `PATH` from `bin/`) |
| `<root checkout>/scripts/merge_pr.py` | `cd <root checkout> && merge_pr.py` |
| `docs/agents/<shared doc>` in skills and agents | `${CLAUDE_PLUGIN_ROOT}/docs/agents/<shared doc>` |
| `subagent_type: "<agent>"` | `subagent_type: "agent-team:<agent>"` |

`docs/agents/project.md`, `docs/agents/installed-from.txt` and `docs/superpowers/...` are the app's own files and are never rewritten. After rewriting, the script fails if any copied `.md` file still names `scripts/` as a path, so a new call style can't slip through as a broken command.

Commands go through `bin/` rather than `${CLAUDE_PLUGIN_ROOT}/scripts/` because the role docs (`trackers/github.md` and the rest) are read with the Read tool, where nothing is substituted. One rule then covers skills, agents and docs. Each `bin/<name>` is a two-line shell wrapper: `exec python3 "$(dirname "$0")/../scripts/<name>" "$@"` for `.py` scripts, and `exec "$(dirname "$0")/../scripts/<name>" "$@"` for `.sh` ones. Wrappers, not symlinks, because the docs don't say how symlinks survive the copy to the plugin cache.

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

New module `agent-team/scripts/app_root.py` with one function, `root()`:

1. If the folder above the script holds `docs/agents/project.md`, return that folder. This is every installed copy and this repo's root links, so their behavior doesn't change.
2. Otherwise return `git rev-parse --show-toplevel` run in the current directory. This is the plugin case: the plugin never contains `project.md`, so rule 1 can't match there.
3. If that fails, return the current directory.

Every `ROOT`, `DEFAULT`, `DEFAULT_FILE`, `DEFAULT_STATE`, `INDEX` and `NOTES` that is built from `__file__` today is built from `app_root.root()` instead, including `project_config.DEFAULT` and `agent_usage.project_name`. Scripts that call `gh.sh` find it next to themselves (`Path(__file__).parent / "gh.sh"`), as `cos_brief.py` does already. `PROJECT_MD` and `COS_STATE_FILE` overrides keep working.

`wait-for-ci.sh` gets the same rule in shell: `cd` to the folder above the script if it holds `docs/agents/project.md`, else to `git rev-parse --show-toplevel`, and call `gh.sh` from the script's own folder.

In the plugin, `merge_pr.py` takes the root checkout from the current directory, which is why the merge-pr skill's line becomes `cd <root checkout> && merge_pr.py`. The gate still can't come from the PR: the plugin copy is the pinned one, not the worktree's.

### 4. Versions

- `plugin/agent-team/.claude-plugin/plugin.json` has `"version": "0.1.0"`. A release is a PR that bumps it (and rebuilds), then a tag `v<version>` on the merge commit, pushed by the approver. Tags are never moved.
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

  The relative-path source means the plugin comes from the same tagged checkout as the marketplace file, and that Claude Code fetches it from project settings alone.
- To move to a newer version, the app's install PR changes `ref` to the new tag.
- `installed-from.txt` keeps meaning what it means today: the commit `install.sh` copied from. A plugin app has no copied team files for Claude Code, so its pin is the `ref` tag. If the app still runs `install.sh` for Cursor or Codex, its install PR runs it from the same tag, so both pins name one commit.

### 5. Hosts

The plugin covers Claude Code only. Cursor and Codex find skills through the repo's `.claude/skills` and `.agents/skills`, so they stay on `install.sh`. An app that runs Claude Code on the plugin and also keeps `install.sh` copies for another host gets both sets of skills in Claude Code (`ship-loop` and `agent-team:ship-loop`) and two Stop hooks; the same-name test below says what that looks like, and the app's switch PR decides what to keep.

`README.md` gets a "Claude Code plugin" section (what it covers, the settings snippet, how to move versions, how to cut a release, how to rebuild). `agent-team/docs/agents/README.md` gets one paragraph on the two install paths.

### 6. Same-name skill test

During the build, before `MERGE READY`, run `claude -p --plugin-dir plugin/agent-team` in a throwaway git repo that has its own `.claude/skills/ship-loop/SKILL.md` with a marker line. Record in the PR body and the as-built: whether both skills load, which one `/ship-loop` runs, which one the model picks when told "use the ship-loop skill", and whether `bin/` is on `PATH` in a subagent's Bash. If `bin/` is not on `PATH` in subagents, the build rewrites skill and agent bodies to `${CLAUDE_PLUGIN_ROOT}/bin/<name>` instead, and the PR says so.

## Tests

Per `AGENTS.md` § Testing, one table-driven test per rule:

- `test_app_root.py`: copy the scripts into a temp folder with no `project.md` (the plugin layout), make a temp app repo with a fixture `project.md`, run each script's root lookup from inside the app (and from a subfolder of it), and check it names the app and its `.agent-team/state.json`. The installed layout (scripts inside the app) keeps returning the script's parent. Covers the ticket's "finding the app root when run from the plugin path".
- `test_plugin_build.py` (skips outside collective-wisdom, like `test_root_links.py`): rebuild into a temp folder and compare with the committed `plugin/agent-team/`, so a skill edit without a rebuild fails CI; check no `project.md` or `test_*.py` is in the plugin; check every `bin/` wrapper's target exists.
- Run the plugin end to end once by hand (not in CI): in a temp app repo with only the plugin enabled through `--plugin-dir`, run a skill, `cos_state.py` through `bin/`, and the Stop hook, and check the app's `.agent-team/state.json` was written. Record it in the PR.
- `test_symlinked_root.py` and `test_root_links.py` keep passing unchanged.

## Calls I made

- **The plugin is a generated, committed copy (`plugin/agent-team/`), not the source files changed in place.** The ticket says "change the skills to call the scripts by the plugin's root path". Changing the source would break `install.sh` apps, Cursor, Codex and this repo's own Chief of Staff, which read the same files. So the source keeps `scripts/...` and the plugin copy gets rewritten paths. Cost: about 100 duplicated files in the repo, and a CI test that fails when someone forgets to rebuild.
- **Plugin commands are bare names on `PATH` (`gh.sh`, `cos_state.py`) through `bin/`, not `${CLAUDE_PLUGIN_ROOT}/scripts/...`.** The role docs hold most of the calls and get no substitution. Fallback to `${CLAUDE_PLUGIN_ROOT}/bin/` in skills if `bin/` isn't on `PATH` in subagents.
- **The plugin ships the shared role docs** (`docs/agents/*` except `project.md`), because the skills and subagents send the model to them. The app's `AGENTS.md` still points at `docs/agents/org-chart.md` in the repo; fixing that is the app's switch PR.
- **Pin by git tag on the marketplace (`ref: v0.1.0`), with the plugin as a relative-path source.** The marketplace `ref` takes a branch or tag, not a SHA. A plugin source can take a `sha`, but then the marketplace file itself still follows a branch. A tag pins both, and the relative path is what lets project settings fetch the plugin.
- **Version 0.1.0, tags `v<version>`, cut by the approver after merge.** This PR adds no tag; the first one comes after merge.
- **Scripts keep finding the app from their own location when that location holds `project.md`,** and use the current git repo only otherwise. Using the current repo everywhere would change `merge_pr.py`, which is run by absolute path from the root checkout while the caller sits in a worktree.
- **Subagent types become `agent-team:<name>` in the plugin.** Skill-to-skill mentions ("invoke `open-pr`") stay as they are; the model finds `agent-team:open-pr`.
- **Plugin name `agent-team`, marketplace name `collective-wisdom`.**
- **`build_plugin.py` lives at the repo root, not in `agent-team/scripts/`,** so it doesn't ship to apps. Its test sits in `agent-team/scripts/` so CI runs it.
- **`install.sh` doesn't change** and doesn't learn a plugin mode. Each app's switch PR edits its own `settings.json`.

## Risks

- The docs' `bin/` and `${CLAUDE_PLUGIN_ROOT}` behavior is checked only by the manual run, not CI.
- Two copies of each skill in an app that keeps `install.sh` files and enables the plugin. The same-name test shows how bad that is before any app tries it.
