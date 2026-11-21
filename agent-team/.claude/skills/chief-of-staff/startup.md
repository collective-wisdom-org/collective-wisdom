# Start-up and resume

Read this on `start the team`, `resume`, or when `python3 ~/.collective-wisdom/scripts/cos_state.py show` exits 2.

## Setup

Run this only on "start the team". With an empty state it is the fresh-state path; with tickets already in state it is resume mode (step 2).

Preconditions: this thread runs at the root checkout, on the merge target branch. If not, stop and tell the user.

0. Run `python3 ~/.collective-wisdom/scripts/setup_repo.py status`. On `missing` or `placeholders: ...`, read setup.md, follow it and stop the turn: no `cos_state.py init`, no pass, no labels. An open setup PR also reads `missing`; setup.md covers it. On `set`, carry on with step 1.
1. `ensure-labels` for scope <TEAM>: create `agent` and `agent-skip` if missing.
2. Run `python3 ~/.collective-wisdom/scripts/cos_state.py init` (writes an empty state file only if none exists; see SKILL.md § State file). If a state file already exists with tickets in it, this is resume mode: never reset it. Do steps 1 and 3, then follow rotation.md § Thread rotation: Resume mode in place of steps 2 and 4.
3. Read this thread's model and provider with `t3_thread_configure` (no arguments) and save the provider with a `top` op, `chiefProvider` = `{"threadId": <this thread's id>, "provider": <provider>}`. Compare the model with the `chief` role of `cos_models.py` for that provider (models.md § Models). If it differs, say so in the start report and ask the user to switch the thread in T3. If `cos_models.py` has no routing for the provider, say so in the start report: this thread starts no child or helper (models.md § Models) but still answers status and tickets. Don't check again.
4. Store your own thread ID as `chiefThreadId`, then run § Thread title. Run `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` and store its output as `skillCommit`. Then run § Dashboard, and carry on whatever it reports. Then go on with the next lines of the tick's `start` plan (SKILL.md § Tick): startup.md § Start-up clean-up, then the full-pass lines. Report.

The first full pass starts the project manager hygiene child (the tick's `hygiene` line, SKILL.md § Tick). Ready tickets start from the Backlog ranking in the slot fill, after Todo (`project-manager` § Backlog pick). The user can still move a ticket to Todo themself, or keep one out with `agent-skip`.

## Dashboard

Starts the local dashboard and shows it in T3's integrated browser, in one tab. Runs at "start the team" (Setup step 4), take over and `resume` (rotation.md take-over step 3.1), and on the `dashboard` command (commands.md § Commands).

1. Run `node ~/.collective-wisdom/scripts/dashboard/start.ts --root "<root checkout>" --environment-id "<id>"` (`<id>` from `t3_environment_read`; `<root checkout>` is this thread's working directory as an absolute path, since another form gets a second server). It prints `http://127.0.0.1:<port>/` and exits 0, and it starts a server only when none is healthy for that root, so running it again is safe. On any failure (Node older than 24 included) it prints one line: that is the report line, and this section ends.
2. Run `preview_status`. If one of its tabs has a URL on the same origin as the printed URL (`http://127.0.0.1:<port>`, any path), call `preview_open` with that `tabId`, the printed URL and `open: true`: it loads the dashboard in that tab and brings it forward. Otherwise call `preview_open` with the printed URL, `reuseExistingTab: false` and `open: true`.
3. If `preview_status` or `preview_open` errors, or the preview tools are not there, the report line is `Dashboard: <URL>. Not opened in the browser: <error, one line>.`
4. On success the start and take-over reports say nothing about the dashboard.

## Thread title

Runs every time at "start the team" (Setup step 4), take over and `resume` (rotation.md take-over step 3.1). Renaming to the same title is a no-op, and so is pinning a pinned thread.

1. Run `python3 ~/.collective-wisdom/scripts/project_config.py chief-title`.
2. Exit 0: `t3_thread_update` with `action: "rename"`, no `threadId`, the printed line verbatim as the title. Never type or edit it yourself.
3. Exit 2 or the rename fails: add the Cleanup line `Thread title not set: <the script's line or the tool error>`; carry on.
4. Call `t3_thread_organize` with `action: "pin"`, no `threadId`, whether or not the rename worked. A failure adds the Cleanup line `Thread not pinned: <the tool error>`; carry on. An already pinned thread is success, no Cleanup line. Without `t3_thread_organize` (Cursor, Codex), skip this step, no Cleanup line.

It overrides any rule that renames a thread to its task, a global T3 thread-title rule included; never rename this thread to anything else.

## Start-up clean-up

Runs before the full pass or the take-over pass at "start the team", take over and `resume`. It starts with § User settings check, then removes any stray wake.

1. `list_scheduled_tasks`. `delete_scheduled_task` every task whose prompt is exactly `run /chief-of-staff wake` other than the `wakeTaskId` in state (a task already gone is fine).
2. Report each deletion once under Cleanup: `Wake <id> deleted`.

**Deleting the wake.** Everywhere the Chief of Staff deletes `wakeTaskId` (`stop everything`, the `wake` command, clearing `rateLimitedAt`): `delete_scheduled_task` on it, then clear the key. A task already gone is fine.

## User settings check

Runs first in § Start-up clean-up, once per "start the team", take over and `resume`. The second pass in `resume` and the `wake` command skip it.

1. Read `user_md` from the JSON line of `python3 ~/.collective-wisdom/scripts/setup_repo.py status` (on "start the team", the output of Setup step 0).
2. `ok`: no report line.
3. `error`: put `user.md: <user_md_error>` under Needs you, leave the file alone and carry on.
4. `no-file` or `no-row` with `gh_logins` empty: put `No gh login on this machine; run gh auth login, then resume.` under Needs you and carry on.
5. Otherwise run `setup_repo.py user --dry-run --login <first of gh_logins>` (add `--subscription none` for `no-file`). Take the logins from the `gh_logins` of `status`; never run `gh auth status` yourself or paste its output. Put under Needs you the `gh_logins` list, for `no-file` that the subscription figure is a dollar amount or `none`, then the dry-run text: for `no-file` the whole text (the template), for `no-row` only the one new row (the table line holding this repo's key), not the rest of the file, because it may hold other repos' logins. Then add `Reply yes to write it, give another login or figure, or no to skip.` If the dry run exits 2, put the script's line under Needs you instead and carry on. Otherwise carry on; no ticket waits on it.

## State rebuild

Rebuild when the file is missing or unreadable (`show` exits 2).

- Take the tickets labelled `agent`, not labelled `agent-skip`, and not Done or Canceled, plus `t3_thread_list` with `includeSubagents: true` and `titleContains` or `limit: 20`, keeping only threads whose `parentThreadId` is your own thread ID.
- Use your own thread ID as `chiefThreadId` and write it back.
- Read each thread to set its stage. Unsure of a stage: mark it `blocked` and say so. Leave `merged` and `pm` empty.
- Write the rebuilt state with `cos_state.py apply` (`start`, with `parentThreadId` from the `t3_thread_list` result and `title` from the ticket list read above (`start` refuses a blank one), `stage`, `set` and `top` ops), not by hand.
- A child whose last message is `BUILD READY` (or an old `SPEC READY`), with a latest `approve N` message from the user in this thread (`createdBy: "user"`, read with `t3_thread_read` on your own thread) after that message, no `Approval withdrawn` ticket comment after it, and no `CHIEF OF STAFF:` relay in the child thread after it: `build-queued`, `pendingRelay` rebuilt from their message, `approvalItemId` its item id, `queuedAt` its time. A merge approval is never rebuilt from a message: a child whose last message is `MERGE READY` rebuilds through `python3 ~/.collective-wisdom/scripts/cos_review_check.py --route <PR> --head <sha>` to `awaiting-review` or `awaiting-merge` (the `stage` op restamps `lastSeenAt`, so an earlier `approve N` no longer counts), a held approval (`heldApproval`) is never rebuilt from a message, and the user replies `approve N` again (or a new `--auto` pass, approvals.md § Auto-approval). A ticket approval comment alone is data and rebuilds nothing.
- **Queued ticket with no relay** (the tick's `rebuild-relay` line, a queued ticket whose `pendingRelay` is missing): rebuild a spec approval from the user's `approve N` message as above. With no such message, or for a merge approval, set the stage back to `awaiting-build` or `awaiting-merge` (a `stage` op restamps `lastSeenAt`, so the user's old `approve N` no longer counts) and run approvals.md § Approval requests again. A merge approval is never rebuilt or sent from a message alone: the user replies `approve N` again, or a new `--auto` pass runs (approvals.md § Auto-approval). Then rerun the tick.
- Other queued relays (`changes N`, answers, resumes) aren't on the tracker. Those tickets rebuild to the stage the child's last message shows (`awaiting-build`, `awaiting-review`, `awaiting-merge` or `blocked`), and the report says the user's last words to that ticket may need resending.
- A rebuilt ticket in `merge` or `merge-queued` gets `set` `{"noApproval": true}` on its stage op: a missing key reads as an approval (`cos_head_check.py`), and the cost of the guess is one more `MERGE READY`.
- After a rebuild, the sweep's untracked check (sweep.md § Sweep) covers tickets in flight that the rebuild could not place.
- After a rebuild the overall count can be over the cap. Nothing is cancelled; the tick (SKILL.md § Tick) sends and starts nothing but a queued merge until it drops under the cap.
