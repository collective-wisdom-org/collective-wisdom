# CW-156: status pane in the plugin marketplace: plan

Spec: [2026-11-05-cw-156-status-pane-marketplace-design.md](../specs/2026-11-05-cw-156-status-pane-marketplace-design.md)

## Task 1: add the marketplace entry

- Add `status-pane` to `plugins` in `.claude-plugin/marketplace.json`: source `./agent-team/.claude/mods/status-pane`, description copied from the mod's `plugin.json`.
- Check: the file parses as JSON, and `claude plugin validate .` passes when the CLI offers it.
- Run `python3 -I -m pytest -q agent-team/scripts` (the repo test command).
