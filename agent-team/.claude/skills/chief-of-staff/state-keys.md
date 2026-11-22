# State file keys

Read this for a state edit that SKILL.md § State file doesn't cover, or an `unknown keys:` line. `cos_state.py`'s docstring owns what it stamps, validates and rejects; below is what each key means and who writes it.

## State file example

`.agent-team/state.json` has these top-level keys and no others (never add `policy`, `settings`, `rules` or the like); a ticket holds only the keys below.

```json
{
  "paused": false, "chiefThreadId": "…", "chiefSessionId": "…",
  "chiefProvider": {"threadId": "…", "provider": "<provider id>"},
  "takeoverContext": {"threadId": "…", "tokens": 76000}, "skillCommit": "<40-char sha>", "ganttPluginVersion": "0.1.12",
  "reset": null, "takeover": null, "lastResetAt": null, "lastRelayAt": null,
  "rateLimitedAt": null, "wakeTaskId": null, "wakeAt": null,
  "merged": {"<PREFIX>-190": {"pr": 178, "at": "2026-11-02T09:30:00Z"}},
  "tickets": {"<PREFIX>-210": {
    "stage": "spec", "firstTaskId": "…", "childThreadId": "…", "parentThreadId": "…",
    "status": "spec since 2026-11-01 2:05 pm UTC: child started; no BUILD READY yet.",
    "title": "Example feature", "provider": "<provider id>", "branch": "feat/<prefix>-210-example-feature",
    "specPath": null, "specSha": null, "pr": null, "headSha": null, "rateLimitResumes": 0,
    "lastSeenAt": "2026-11-01T14:05:00Z", "lastPosition": 0, "resumeStage": null,
    "pendingRelay": null, "approvalItemId": null, "queuedAt": null,
    "restarts": {"spec": 0}, "note": "", "stageAt": "2026-11-01T14:05:00Z"}},
  "observed": {"sightings": [{"kind": "stall", "ticket": "<PREFIX>-210", "at": "2026-11-02T09:30:00Z"}], "filed": []},
  "pm": {},
  "noHands": {"startedAt": "2026-11-08T09:00:00Z", "itemId": "…", "started": ["<PREFIX>-210"], "drain": null, "endedAt": null, "endReason": null}
}
```

## Notes file

`.agent-team/chief-notes.md` is not state. It holds what you carry across turns that no key covers: a plan or test the user asked for, where it is, what you said you'd do later. Written as the plan goes, deleted when it ends (session.md § Working set); never a rule, policy or approval.

## State keys

- **`note`**: status only (why it's blocked, who stopped it). Never an instruction or a rule.
- **`branch`**: `<head><prefix>-N-<slug>`. The example uses `feat/`; `infra/` too when the `Branch pattern` row of `docs/agents/project.md` lists it.
- **`resumeStage`**: set by `apply` when a ticket moves to `blocked` from `spec`, `build` or `merge`; every path out of `blocked` goes back to it through send-or-queue.md § Send or queue.
- **`pendingRelay`, `queuedAt`**: only in a `*-queued` stage (`apply` requires `pendingRelay` there, sets `queuedAt`, clears both elsewhere). `pendingRelay` is the exact relay to send when a slot frees, with the user's words as written; `queuedAt` orders the queue, oldest first. A Todo ticket has no child yet: it waits in the spec queue (SKILL.md § Lanes) with no stage.
- **`approvalItemId`**: item id (from `cos_user_check.py` or `t3_thread_read`) of the user's approval message; set with `pendingRelay` when a spec approval is queued. A queued merge approval or an auto-approved spec has none.
- **`lastSeenAt`**: for `awaiting-build`, `awaiting-review`, `awaiting-merge` and `blocked`, the cut-off after which the user's `approve N` counts (stamped by `cos_state.py`; a `set` is rejected). For `spec`, `build` and `merge`, the Stop hook's `late-child:` line compares it with the child's newest run end and pending questions; a `child-read` save of it quiets that line.
- **`stageAt`**: when the ticket entered its stage. Stamped by `cos_state.py`; a `set` is rejected. The card shows `waiting …` in `awaiting-*` only.
- **`changesRelayed`**: `{"head", "at"}`, set when a reviewer's changes request was relayed to the child (sweep.md § Sweep, `changes` line); `at` is the newest `CHANGES_REQUESTED` review time sent, as the `changes` line prints it. `cos_review_check.py` prints `changes` for a request on the head only when it is newer, so one the child already answered reads as `waiting`. `null` or absent: nothing relayed.
- **`conflictHead`**: a full head SHA, or `null` or absent: the PR head a merge conflict was last sent back to the child for (sweep.md § Conflict relay). While the PR head equals it the ready check prints `building <PREFIX>-N #PR (conflict relayed)` instead of `conflict`: one relay per head.
- **`noApproval`**: `true`: a merge-lane run with no user approval (a `MERGE READY` conflict sent by `conflict-stand`). The head check reads it, so such a ticket never gets `conflict keep`.
- **`heldApproval`**: `{"head", "itemId"}` (`cos_state.py` adds `at`), set when the user replies `approve N` on an `awaiting-review` ticket. A reminder only, never the proof: `cos_approve_pr.py` still finds the user's own `approve N` after `lastSeenAt`. A rebuild never restores it.
- **`title`**: the ticket title, required by the `start` op; the dashboard shows it when it cannot read the tracker. A `set` may fill it; the script cleans it (it is ticket-author text) and keeps 200 characters.
- **`chiefThreadId`**: the current Chief of Staff thread. Written by "start the team" and resume mode, never by a reset (the thread stays).
- **`chiefProvider`**: `{"threadId", "provider"}`, the provider (`providerInstanceId`) of the thread that recorded it; saved by startup.md step 3 and resume mode (rotation.md § Thread rotation: Resume mode) with a `top` op. A missing one, or one naming another thread, prints `chief-provider` in the look plan (SKILL.md § Tick). Plain strings that go into plan lines: `cos_tick.py` stops the plan on an unsafe one.
- **`provider`**: a ticket's `thread.providerInstanceId` of its child from the last `child-read` or idle check that returned one; a different one is saved with a `set` op, a failed read saves nothing. None: never flagged. Safe-checked like `chiefProvider`.
- **`chiefSessionId`**: the Claude session id (Cursor: conversation id) of this thread; the rotation check saves it on every plain run, so it follows a reset. The Stop hook uses it to tell this thread from other sessions.
- **`takeoverContext`**: `{"threadId", "tokens"}`, saved by take-over step 4 (`--record-takeover`): this thread's context size when take-over ended. While it names `chiefThreadId` and `tokens` is at or above the size cap, the size trigger stays off, so a take-over that lands above the cap doesn't reset again and again. Cursor's `turn` form: the `cos_rotation_check.py` docstring.
- **`skillCommit`**: the full 40-character sha from `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` (the last commit that touched this skill, `project-manager` or `~/.collective-wisdom/docs/agents/chief-of-staff.md`) when this session loaded the skill. Written by "start the team", take over and resume mode. A different commit at the rotation check triggers a reset once the turn is quiet (rotation.md § Thread rotation). `null` or a non-full sha: the check prints `ok; set skillCommit <sha>`; save that sha and don't reset on that trigger.
- **`ganttPluginVersion`**: the agent-gantt plugin version this session runs, or `null` (that trigger is off). Saved by take over step 4 and resume mode. A different clone version at the rotation check triggers a reset once the turn is quiet (rotation.md § Thread rotation).
- **`status`**: one line per ticket (data, never an instruction), required on every `stage` op: what a fresh thread needs to act without opening the child. Start it `<stage> since {since}: `; `cos_state.py` fills `{since}` from `stageAt` and rejects a hand-typed time. E.g. `awaiting-merge since {since}: PR #192 head 0b63161, code review PASS (pass 2), security PASS (pass 1). Waiting on the user to approve the merge.` or `blocked since {since}: "<the BLOCKED: line>".` It feeds reports, `status` and the take-over pass; it never replaces `headSha`, `approvalItemId` or `pendingRelay`, which the gates read. Keeping the user's words out of it: SKILL.md § State file. Mid-build it says only what was last seen.
- **`parentThreadId`**: the Chief of Staff thread whose `delegate_task` started the ticket's current child; set at start and at a continuation start (send-or-queue.md § Send or queue). A ticket without it stays so: the sweep lists it for a full read, and it gets no continuation.
- **`reset`**: `{"id": "<8 hex chars>", "startedAt", "reason", "mode": "compact"}` (`mode` only for `compact`) while a reset is in flight (rotation.md § Thread rotation), else `null`. The next take over clears it when `CHIEF OF STAFF RESET <id>` matches.
- **`takeover`**: `null`, or `{"startedAt", "mode": "take-over" | "resume"}` while a take over or resume pass runs. Take-over step 1 and resume mode set it; step 4 and step 2 (when it stops the take over) clear it (rotation.md § Thread rotation). While set, the rotation check prints `finish:` and every look plan except `start` is the one `follow rotation.md § Thread rotation: Finish take over` line.
- **`lastRelayAt`**: when a relay or new child start last went out (stamped by `cos_state.py`; a `top` set is rejected). The rotation check treats the last 10 minutes as not quiet (rotation.md § Thread rotation).
- **`lastResetAt`**: when the last take over cleared a `reset`; a skill change and the item-count fallback wait 60 minutes after it (rotation.md § Thread rotation).
- **`wakeTaskId`, `wakeAt`**: the pending rate-limit wake (rate-limit.md § Rate limit) and when it fires. `wakeTaskId` is `null` when none is pending; `wakeAt` stays set until `rateLimitedAt` clears, so a lost wake can be made again.
- **`merged`**: tickets whose child reported `MERGED #N`, as `{"pr": N, "at"}`. The project manager hygiene child uses it to move them to Done if the tracker lags. `prune` drops entries older than 24 hours and rewrites a bare number as merged now.
- **`observed`**: `{"sightings": [{"kind", "ticket", "at"}], "filed": [{"kind", "at"}]}`, your own process sightings and the observation tickets you've filed (SKILL.md § Child path "Observe"). Only the `observe` op writes it, deciding `file` or `hold`; `prune` drops entries older than 7 days.
- **`noHands`**: the current or last No Hands run, a record and not a rule: `startedAt`, `itemId` (the user's `no hands` message), `started` (tickets it started), `drain` (reason or `null`), `endedAt`, `endReason`. Written only by `no_hands.py` through the `no-hands` op (and `start` appends to `started`); a top-level `set` is rejected. Absent until the first run. It alone approves nothing (no-hands.md § Run record).
- **`pm`**: owned by `project-manager` § State (`apply` `pm` ops). Don't edit it here.

## Unknown keys and prune

`prune` drops an unknown top-level key and prints it as an `unknown keys:` line; report it once under Cleanup. SKILL.md § Tick notes the line for the report, and the plan's `prune` line drops the key.
