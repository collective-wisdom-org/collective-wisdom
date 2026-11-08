# Kill switch and resume

Read this on `stop everything` or `resume`.

## Kill switch

On "stop everything":

1. `task_cancel(firstTaskId)` for every running child.
2. If state has `wakeTaskId`, delete it as startup.md § Deleting the wake says and clear `wakeTaskId`. Keep `wakeAt` and `rateLimitedAt`: `resume` makes the wake again.
3. `top` op: `paused: true`.
4. `stage` op to `blocked` for every ticket in `spec`, `build` or `merge`, with `set: {"note": "stopped by the user"}`; `apply` sets `resumeStage`. Queued tickets stay queued.

5. If a No Hands run is active (`noHands` has `startedAt` and no `endedAt`), end it: `python3 ~/.collective-wisdom/scripts/no_hands.py end stopped-by-user`, then post the summary (no-hands.md § End a run).

Leave worktrees and branches in place. A No Hands stop (no-hands.md) runs steps 1 to 4 with the note `stopped by No Hands: <why>` in place of `stopped by the user`, then ends the run with its own reason. A ticket in `merge` is not blocked by a No Hands stop: after `task_cancel`, `stage` op it back to `awaiting-merge` (note `stopped by No Hands: <why>`), and decide it again as for any merge that reached that stage (approvals.md § Auto-approval; the tolerance now, since the run is over). Only `spec` and `build` tickets go to `blocked`.

## Resume

On `resume`:

1. Clear `paused`.
2. For each blocked ticket whose note is "stopped by the user" or starts with "stopped by No Hands:", relay `CHIEF OF STAFF: continue the <stage> stage from where the branch is.` through SKILL.md § Send or queue to the lane of its `resumeStage`. Other blocked tickets stay blocked.
3. `resume` never starts a No Hands run, and an ended run stays ended. The relays in step 2 go under the tolerance. The user says `no hands` for a new run.
4. Then run startup.md § Start-up clean-up and the lean take-over pass (rotation.md § Thread rotation "Take over" step 4), which makes a wake if a rate limit still needs one.
