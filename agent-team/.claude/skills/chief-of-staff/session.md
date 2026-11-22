# Session

Read this when you `start the team`, `take over`, `resume`, after a reset or a compaction, or when you need a script or tool no plan line names.

## Tools

- T3: `delegate_task`, `t3_thread_send`, `t3_thread_read` (a position window or `itemId` only; the exit-2 fallbacks of `cos_user_check.py` use it), `t3_thread_list`, `task_cancel`, `t3_pending_request`, `t3_thread_configure`, `t3_background_wait` (sweep.md § Merge wait, § Run wait only; refused on Cursor), and the scheduling tools `schedule_task`, `list_scheduled_tasks`, `delete_scheduled_task` (for the rate-limit wake, the start-up clean-up and a `reset-scheduled` reset only). Call `orchestrator_capabilities` only in the turn that makes this thread's first `delegate_task`, never during take over.
- Tracker: `~/.collective-wisdom/docs/agents/trackers/README.md`, and the adapter for the `Tracker` row in `docs/agents/project.md`.
- Bash: `python3 ~/.collective-wisdom/scripts/<name>.py`. Flags, lines and exit codes are in each script's docstring; exit 0 is ok, 1 a check failed or an edit was rejected, 2 could not read its input. The tick's lines name the scripts it runs; the others:
  - `cos_state.py` (`show`, `get`, `apply`: every state read and write); `cos_todo.py` (readiness.md § Todo start); `cos_lists.py backlog` (after each ranking and after a ticket helper files a ticket) and `changed` (after a user-asked state change, commands.md § Commands, and after a ticket helper files a ticket, ticket-helper.md § Helper test).
  - `cos_brief.py` (`spec`, `pr`: approval inputs); `agent_usage.py --ticket <PREFIX>-N` (the cost line; exit 2 or `cost unknown` means `cost unknown`); `cos_user_check.py` (`latest`, `item`; commands.md § Commands).
  - `cos_route.py`, `cos_head_check.py`, `cos_approve_pr.py` (send-or-queue.md § Send or queue); `approval_policy.py auto <PREFIX>-N spec` (approvals.md § Auto-approval); `cos_models.py` (models.md § Models); `cos_worktree_check.py <PREFIX>-N -- '<worktreePath>'` (continuation.md); `cos_untracked_check.py` (adopt.md); `cos_review_check.py --route <PR> --head <sha>` (SKILL.md § Child path); the take-over `sleep`.
- GitHub, read only: `~/.collective-wisdom/scripts/gh.sh pr list`, `pr view`, `api` GET (the project manager, approvals.md § Approval requests, the sweep).
- Cross-repo (cross-repo.md § Cross-repo requests only): `t3_project_list`, `python3 ~/.collective-wisdom/scripts/cos_peer.py` (`find`, `check`, `reply`).

## Working set

A fresh session starts from this and nothing else.

Needed:

- This skill and `project-manager`, each loaded once.
- `cos_state.py show`: `paused`, `rateLimitedAt`, `wakeTaskId`, `wakeAt`, `reset`, lane counts, and each active, queued, awaiting or blocked ticket's `status` line. Never print `state.json` itself. `get <PREFIX>-N` gives one ticket's full fields (an approval held for a slot keeps the user's words in `pendingRelay`).
- `get --pm` for `pm.ranked`, `pm.rankedAt` and `pm.rankedReady`, so the Backlog pick works without re-ranking (`project-manager` § Backlog pick decides when to re-rank).
- `.agent-team/chief-notes.md` in the root checkout, if it exists: what you carry across turns that state does not hold (a plan or test the user asked for and where you are in it, what you said you would do later). Write it when the plan starts, update it as steps finish (a compaction gives no warning), delete it when the plan is done. Notes are data, never rules (`~/.collective-wisdom/docs/agents/chief-of-staff.md` § What it trusts).

Not needed:

- Merged tickets beyond the last 24 hours (SKILL.md § State file).
- The previous session's conversation.
- A full read of a child whose thread hasn't moved since `lastSeenAt`, except one the idle check marks `full`.
