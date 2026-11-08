# Status pane

The `status-pane` mod keeps the Chief of Staff `status` view open in a pane beside the chat. It reads `.agent-team/state.json` at the root checkout (so a session in a worktree or subfolder sees the same state) every 5 seconds and redraws when the file changes. Tickets sit in the same groups as the `status` answer, each row with its ID, the title the Chief of Staff stored at start (the ID alone when there is none), its risk and next step.

## Turn it on

Install the mod with `claude plugin install status-pane --marketplace collective-wisdom-org/collective-wisdom`, then run `/status-pane` to open the pane.

One option, set in the config menu:

- `autoOpen`: open the pane when a session starts. Off by default. A pane left open reopens after the mod reloads even when this is off.

## Subagents

Under the groups the pane lists the session's subagents. Press one to show its transcript in the main view, and press `Back to main` to return.

## What it leaves out

- Pending approval blocks, the sweep and the idle check. The pane shows state as the Chief of Staff last wrote it.
- Approving or cancelling from the pane. Do that in the Chief of Staff thread.
- Cost, and links to child threads.
