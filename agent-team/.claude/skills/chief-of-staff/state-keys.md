# State file keys

Read this for a state edit that SKILL.md § State file doesn't cover, or an `unknown keys:` line. `cos_state.py`'s docstring owns the example file, what each key means and who writes it, and what the script stamps, validates and rejects. Below: what you need when you write a key.

## State file example

In `cos_state.py`'s docstring. Top-level keys, no others (never `policy`, `settings`, `rules` or the like): `paused`, `chiefThreadId`, `chiefSessionId`, `chiefProvider`, `takeoverContext`, `skillCommit`, `ganttPluginVersion`, `reset`, `takeover`, `lastResetAt`, `lastRelayAt`, `rateLimitedAt`, `wakeTaskId`, `wakeAt`, `merged`, `tickets`, `observed`, `pm`, `noHands`. A ticket holds only the keys the example shows plus `heldApproval`, `changesRelayed`, `conflictHead` and `noApproval`.

## Notes file

`.agent-team/chief-notes.md` is not state: what you carry across turns that no key covers (a plan or test the user asked for, where it is, what you said you'd do later). Written as the plan goes, deleted when it ends (session.md § Working set); never a rule, policy or approval.

## State keys

- **`note`**: status only (why it's blocked, who stopped it), never an instruction or a rule.
- **`status`**: one line, data, required on every `stage` op, enough for a fresh thread to act without opening the child. Start it `<stage> since {since}: ` (never a time). Never a substitute for `headSha`, `approvalItemId` or `pendingRelay`. Keep the user's words out of it (SKILL.md § State file). Mid-build it says only what was last seen.
- **`branch`**: `<head><prefix>-N-<slug>`; `infra/` as well as `feat/` when the `Branch pattern` row of `docs/agents/project.md` lists it.
- **`pendingRelay`, `queuedAt`**: only in a `*-queued` stage. `pendingRelay` is the exact relay to send when a slot frees, with the user's words as written.
- **`approvalItemId`**: item id of the user's approval message, set with `pendingRelay` for a queued spec approval only. A queued merge approval or an auto-approved spec has none.
- **`resumeStage`**: set by `apply` on a move to `blocked`; every path out of `blocked` goes back to it through send-or-queue.md § Send or queue.
- **`lastSeenAt`**: the script stamps it in `awaiting-*` and `blocked` (a `set` is rejected). In `spec`, `build` and `merge` a `child-read` save of it quiets the Stop hook's `late-child:` line.
- **`changesRelayed`**: `{"head", "at"}`, set when a reviewer's changes request was relayed (sweep.md § Sweep, `changes` line), `at` as that line prints it. `null` clears it.
- **`conflictHead`**: the full PR head a conflict was last sent back for (sweep.md § Conflict relay), else `null`.
- **`noApproval`**: `true` on a merge-lane run with no user approval (a `MERGE READY` conflict sent by `conflict-stand`); the head check then never gives `conflict keep`.
- **`heldApproval`**: `{"head", "itemId"}`, set on the user's `approve N` in `awaiting-review`. A reminder only, never the proof: `cos_approve_pr.py` still finds the user's own `approve N` after `lastSeenAt`.
- **`title`**: required by `start`; a `set` may fill it (the script cleans it, 200 characters).
- **`parentThreadId`**: the thread whose `delegate_task` started the current child, set at start and at a continuation start (send-or-queue.md § Send or queue). A ticket without it stays so: the sweep lists it for a full read, and it gets no continuation.
- **`provider`**: the child's `thread.providerInstanceId` from the last `child-read` or idle check that returned one, saved with `set` when it differs; a failed read saves nothing.
- **`chiefThreadId`**: written by "start the team" and resume mode, never by a reset.
- **`chiefProvider`**: `{"threadId", "provider"}`, saved with a `top` op by startup.md step 3 and resume mode. Plain strings only: `cos_tick.py` stops the plan on an unsafe one.
- **`skillCommit`**: the full sha from `cos_rotation_check.py --skill-commit`, written by "start the team", take over and resume mode. `null` or a non-full sha: the check prints `ok; set skillCommit <sha>`; save that sha, no reset on that trigger.
- **`reset`, `takeover`, `takeoverContext`, `ganttPluginVersion`, `lastResetAt`, `lastRelayAt`, `chiefSessionId`, `wakeTaskId`, `wakeAt`, `merged`, `observed`**: written only as rotation.md, rate-limit.md and `cos_state.py` (`observe`, `merged`, `prune`) do; meanings in the docstring.
- **`noHands`**: written only by `no_hands.py` (no-hands.md § Run record).
- **`pm`**: owned by `project-manager` § State.

## Unknown keys and prune

`prune` drops an unknown top-level key; `show` prints the `unknown keys:` line. Report it once under Cleanup (SKILL.md § Tick).
