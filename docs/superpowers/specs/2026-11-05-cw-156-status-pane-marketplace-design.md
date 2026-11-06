# CW-156: status pane in the plugin marketplace

**Status:** Draft
**Ticket:** [#156](https://github.com/collective-wisdom-org/collective-wisdom/issues/156)

## Goal

`/plugin install status-pane@collective-wisdom` installs the status pane on a machine, the way `agent-gantt` installs.

## Today

- `.claude-plugin/marketplace.json` lists one plugin, `agent-gantt`, with source `./mods/agent-gantt`.
- The status pane lives at `agent-team/.claude/mods/status-pane/` with its own `.claude-plugin/plugin.json`. `install.sh` copies it into apps; there is no per-machine install.
- `AGENTS.md` says the marketplace file lives outside `agent-team/` and is edited in place.

## Builds

- A second entry in `.claude-plugin/marketplace.json`: name `status-pane`, source `./agent-team/.claude/mods/status-pane`, and the description from the mod's `plugin.json`.

## Leaves out

- Any change to the mod or to what `install.sh` copies.
- A test. The change is one JSON entry, and `AGENTS.md` § Testing skips constants and registries.

## Calls I made

- **The source points into `agent-team/`.** The mod's one copy lives there, so the marketplace entry references it instead of a second copy.
- **No docs change.** `agent-team/docs/agents/status-pane.md` describes the `install.sh` route, which stays as is. The marketplace route is not added there because that file ships to apps and the marketplace is not shipped.

## Touches

none of: data, money, auth, user email, migrations.
