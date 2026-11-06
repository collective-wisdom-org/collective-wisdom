# Status pane

The `status-pane` mod keeps the Chief of Staff `status` view open in a pane beside the chat. It reads `.agent-team/state.json` at the root checkout (so a session in a worktree or subfolder sees the same state) every 5 seconds and redraws when the file changes. Tickets sit in the same groups as the `status` answer, each row with its risk and next step.

## Turn it on

The install copies the mod to `.claude/mods/status-pane/`. Load it as a mod in Claude Code, then run `/status-pane` to open the pane.

Two options, set in the config menu:

- `autoOpen`: open the pane when a session starts. Off by default. A pane left open reopens at the next session start even when this is off.
- `environmentId`: the T3 environment ID, which the thread links need.

## Find the environment ID

Any thread link T3 prints looks like `t3-thread://v2/<environment id>/<thread id>`. The environment ID is the middle part. Copy it into the `environmentId` option. Without it the rows show no thread links.

## Subagents

Under the groups the pane lists the session's subagents. Press one to show its transcript in the main view, and press `Back to main` to return.

## What it leaves out

- Pending approval blocks, the sweep and the idle check. The pane shows state as the Chief of Staff last wrote it.
- Approving or cancelling from the pane. Do that in the Chief of Staff thread.
- Cost, and ticket titles from the tracker. State has no title field, so a row shows the ticket ID alone.
