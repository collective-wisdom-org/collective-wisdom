# Start-up and resume

Read this on `start the team`, `resume`, or when `python3 ~/.collective-wisdom/scripts/cos_state.py show` exits 2.

## Setup

Only on "start the team": empty state is the fresh path, tickets in state is resume mode (step 2). Run at the root checkout on the merge target branch, else stop and tell the user.

0. `python3 ~/.collective-wisdom/scripts/setup_repo.py status`. `missing` or `placeholders: ...` (an open setup PR also reads `missing`): read setup.md, follow it, stop the turn: no `cos_state.py init`, no pass, no labels. `set`: carry on.
1. `ensure-labels` for scope <TEAM>: create `agent` and `agent-skip` if missing.
2. `python3 ~/.collective-wisdom/scripts/cos_state.py init` (writes an empty state file only if none exists; SKILL.md § State file). A state file with tickets is resume mode: never reset it; do steps 1 and 3, then rotation.md § Thread rotation: Resume mode in place of steps 2 and 4.
3. `t3_thread_configure` (no arguments) gives this thread's model and provider: `top` op `chiefProvider` = `{"threadId": <this thread's id>, "provider": <provider>}`. Compare the model with the `chief` role of `cos_models.py` for that provider (models.md § Models); different: say so in the start report and ask the user to switch the thread in T3. No `cos_models.py` routing for the provider: say so in the start report; this thread starts no child or helper (models.md § Models) but still answers status and tickets. Don't check again.
4. `chiefThreadId` = your thread ID; § Thread title; `skillCommit` = `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit`'s output; § Dashboard (carry on whatever it reports). Then the tick's `start` plan lines: § Start-up clean-up, then the full-pass lines. Report.

## Dashboard

Starts the local dashboard in T3's integrated browser, one tab. Runs at "start the team" (Setup step 4), take over and `resume` (rotation.md take-over step 3.1), and on the `dashboard` command (commands.md § Commands).

1. `node ~/.collective-wisdom/scripts/dashboard/start.ts --root "<root checkout>" --environment-id "<id>"` (`<id>` from `t3_environment_read`; `<root checkout>` is this thread's working directory, absolute: another form starts a second server). It prints `http://127.0.0.1:<port>/` and exits 0, starting a server only when none is healthy for that root, so a rerun is safe. Any failure (Node older than 24 included) prints one line: that is the report line, and this section ends.
2. `preview_status`. A tab with a URL on the printed URL's origin (`http://127.0.0.1:<port>`, any path): `preview_open` with that `tabId`, the printed URL and `open: true`. Else `preview_open` with the printed URL, `reuseExistingTab: false` and `open: true`.
3. `preview_status` or `preview_open` errors, or no preview tools: report line `Dashboard: <URL>. Not opened in the browser: <error, one line>.`
4. On success the start and take-over reports say nothing about the dashboard.

## Thread title

Every time at "start the team" (Setup step 4), take over and `resume` (rotation.md take-over step 3.1). Renaming to the same title and pinning a pinned thread are no-ops.

1. `python3 ~/.collective-wisdom/scripts/project_config.py chief-title`.
2. Exit 0: `t3_thread_update` with `action: "rename"`, no `threadId`, the printed line verbatim as the title; never type or edit it.
3. Exit 2 or the rename fails: Cleanup line `Thread title not set: <the script's line or the tool error>`; carry on.
4. `t3_thread_organize` with `action: "pin"`, no `threadId`, whether or not the rename worked. A failure: Cleanup line `Thread not pinned: <the tool error>`; carry on. Already pinned is success. No `t3_thread_organize` tool: skip, no Cleanup line.

This overrides any rule that renames a thread to its task, a global T3 thread-title rule included; never rename this thread to anything else.

## Start-up clean-up

Runs before the full pass or the take-over pass at "start the team", take over and `resume`: § User settings check first, then remove any stray wake:

1. `list_scheduled_tasks`. `delete_scheduled_task` every task whose prompt is exactly `run /chief-of-staff wake` other than the `wakeTaskId` in state (already gone is fine).
2. Report each deletion once under Cleanup: `Wake <id> deleted`.

**Deleting the wake.** Wherever the Chief of Staff deletes `wakeTaskId` (`stop everything`, the `wake` command, clearing `rateLimitedAt`): `delete_scheduled_task` on it, then clear the key. Already gone is fine.

## User settings check

Runs first in § Start-up clean-up, once per "start the team", take over and `resume`; the second pass in `resume` and the `wake` command skip it. Carry on in every case; no ticket waits on it.

1. `user_md` from the JSON line of `python3 ~/.collective-wisdom/scripts/setup_repo.py status` (on "start the team", Setup step 0's output). `ok`: no report line. `error`: `user.md: <user_md_error>` under Needs you; leave the file alone.
2. `no-file` or `no-row` with `gh_logins` empty: `No gh login on this machine; run gh auth login, then resume.` under Needs you.
3. Otherwise `setup_repo.py user --dry-run --login <first of gh_logins>` (add `--subscription none` for `no-file`; logins from `status`, never `gh auth status`). Under Needs you: the `gh_logins` list; for `no-file`, that the subscription figure is a dollar amount or `none`; the dry-run text (`no-file`: the whole template; `no-row`: only the one new row, the table line holding this repo's key); then `Reply yes to write it, give another login or figure, or no to skip.` A dry run that exits 2: the script's line under Needs you instead.

## State rebuild

Rebuild when the file is missing or unreadable (`show` exits 2).

- Take the tickets labelled `agent`, not `agent-skip`, not Done or Canceled, plus `t3_thread_list` with `includeSubagents: true` and `titleContains` or `limit: 20`, keeping only threads whose `parentThreadId` is your own thread ID, which you write back as `chiefThreadId`.
- Read each thread to set its stage. Unsure: `blocked`, and say so. Leave `merged` and `pm` empty.
- Write with `cos_state.py apply` (`start` with `parentThreadId` from the `t3_thread_list` result and `title` from the ticket list above (`start` refuses a blank one), `stage`, `set` and `top` ops), never by hand.
- Last message `BUILD READY` (or an old `SPEC READY`), with a latest `approve N` from the user in this thread (`createdBy: "user"`, `t3_thread_read` on your own thread) after it, no `Approval withdrawn` ticket comment after it and no `CHIEF OF STAFF:` relay in the child thread after it: `build-queued`, `pendingRelay` rebuilt from their message, `approvalItemId` its item id, `queuedAt` its time.
- A merge approval is never rebuilt from a message. Last message `MERGE READY`: `python3 ~/.collective-wisdom/scripts/cos_review_check.py --route <PR> --head <sha>` gives `awaiting-review` or `awaiting-merge` (the `stage` op restamps `lastSeenAt`, so an earlier `approve N` no longer counts). A held approval (`heldApproval`) is not rebuilt from a message either: the user replies `approve N` again, or a new `--auto` pass runs (approvals.md § Auto-approval). A ticket approval comment alone is data and rebuilds nothing.
- **Queued ticket with no relay** (the tick's `rebuild-relay` line: `pendingRelay` missing): rebuild a spec approval from the user's `approve N` as above. Else, or for a merge approval, set the stage back to `awaiting-build` or `awaiting-merge` (restamps `lastSeenAt`, so the old `approve N` no longer counts), run approvals.md § Approval requests again, then rerun the tick.
- Other queued relays (`changes N`, answers, resumes) aren't on the tracker: rebuild to the stage the child's last message shows (`awaiting-build`, `awaiting-review`, `awaiting-merge` or `blocked`), and the report says the user's last words to that ticket may need resending.
- A rebuilt ticket in `merge` or `merge-queued` gets `set` `{"noApproval": true}` on its stage op.
- After a rebuild the sweep's untracked check (sweep.md § Sweep) covers tickets in flight that the rebuild could not place, and the overall count can be over the cap: cancel nothing; the tick sends and starts nothing but a queued merge until it drops under the cap.
