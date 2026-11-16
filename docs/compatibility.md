# Compatibility

What the agent team does on each harness and each ticket tracker, and where it does not. Read this before you adopt the team on a setup other than Claude Code in T3 Code with GitHub Issues. It is this repo's own page and is not shipped to apps.

Last checked against the code on 2026-11-15, after the WISE-441 Cursor trial run ([#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441)) recorded below. Earlier notes: CW-300 ([#301](https://github.com/collective-wisdom-org/collective-wisdom/pull/301)), CW-315 ([#315](https://github.com/collective-wisdom-org/collective-wisdom/issues/315)), CW-316 ([#316](https://github.com/collective-wisdom-org/collective-wisdom/issues/316)), CW-459 ([#460](https://github.com/collective-wisdom-org/collective-wisdom/pull/460)). Recorded runs are in [Runs](#runs).

## Legend

| Value | Meaning |
|---|---|
| 🟢 works | The code shows it, or the team runs it today. A run that no doc records is named in a note |
| 🟡 partial | Part of it works. The cell says what does not |
| 🔴 not supported | Nothing here makes it work on this column |
| ⚪ untested | Nothing shows it either way: the code does not show it and the team does not run it |

A cell is `works` only where the code shows it or the team runs it today. Anything not shown either way is `untested`.

Each cell starts with a colored circle so a column reads at a glance: 🟢 works, 🟡 partial, 🔴 not supported, ⚪ untested. GitHub markdown tables cannot color a cell, so the circle is only a visual aid. The word after it is the source of truth.

A cell that is not `works` gives a short reason and a gap number such as `G3`. The [Gaps](#gaps) list holds one line per gap with its ticket link, or `none yet` while there is no ticket.

The team needs GitHub for code on every tracker. The PR flow, the merge gate and the CI wait call `~/.collective-wisdom/scripts/gh.sh` whatever the tracker is. Other code hosts are out of scope.

## Matrix 1: harnesses

Columns are the places a person runs an agent session. Each column is a T3 Code thread running that harness. The team is built for T3 Code, so sessions without it are not covered.

| Feature | Claude Code in T3 Code | Codex in T3 Code | Cursor in T3 Code | Antigravity in T3 Code |
|---|---|---|---|---|
| Install (skills and instruction block) | 🟢 works | 🟢 works | 🟢 works: WISE-441 CoS quoted `head -n 1 ~/.cursor/rules/collective-wisdom.mdc` → `---` before skill reads (G1) | 🔴 not supported: `install.sh` writes nothing for it (G17) |
| Team skills load | 🟢 works | ⚪ untested (G2) | 🟢 works | ⚪ untested (G18) |
| Subagents | 🟢 works | ⚪ untested: role file as prompt (G4) | 🟡 partial: WISE-441 CT-7 started implementer and dual-review subagents on `cursor`/`default` (`model: inherit`); whether `readonly` blocks MCP writes is unchecked (G4) | ⚪ untested: role file as prompt (G4) |
| Chief of Staff thread | 🟢 works | ⚪ untested (G2) | 🟢 works | ⚪ untested (G18) |
| Ship loop child threads | 🟢 works | 🔴 not supported yet: no model routing recorded (CW-280, G2) | 🟡 partial: WISE-441 CT-7 Cursor child reached `MERGE READY` with code+security PASS on `cursor`/`default`; merge not recorded in this write-up; earlier CT-4 closeout used `composer-2.5-fast` (G3) | 🔴 not supported yet: no model routing recorded (CW-280, G18) |
| Context reset (rotation check) | 🟢 works: mode `reset`, from the CW-315 record; the context size after the reset (G30) and a finish notice reaching the new session (G29) are unconfirmed | 🔴 not supported: mode `none`, no CW-315 run; no Stop hook (G7, G28) | 🔴 not supported: mode `none`, no CW-315 run; the hook sends no `rotate:` line but can still send `finish:` or `late-child:` (G8, G28) | 🔴 not supported: no Chief of Staff (G7, G18) |
| Fresh-context reset (T3 Code after 0.1.9) | 🟡 partial: checks 1 to 5 passed as graded by the user on 2026-11-14, but the context size after the reset is unconfirmed (G30), a notice lost across the reset was recovered by the idle check (G29) and a queued /compact truncated the Chief of Staff skill in that run; since CW-329 the core fits the budget it measured, held by a size test and not re-run live (G25) | ⚪ untested: not run (G2, G28) | 🟡 partial: WISE-441 hand reset (`freshContext: true`) kept the thread id, new `chiefSessionId` + transcript, take-over from state; late-child notices after reset seen (G28, G29); post-reset context size unreadable (G30, [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462)); mode stays `none` | ⚪ untested (G18) |
| Usage and cost report | 🟢 works | 🔴 not supported: reads Claude Code and Cursor runs only (G8) | 🟡 partial: Auto (`default`) runs are priced at a ceiling rate and the `--ticket` line says `(Auto at the ceiling rate)` after `Cursor $Y` (WISE-442, G8); a run on a model with no price (Grok 4.6, Gemini) is still `cost unknown`; `grok-4.7`/`composer-2.5` pricing notes unchanged | 🔴 not supported: reads Claude Code and Cursor runs only (G8) |
| Local dashboard | 🟢 works | 🟡 partial: no gantt rows or spend (G9) | 🟡 partial: WISE-441 dashboard started; Cursor hooks wrote `.agent-team/gantt/` snapshots with `model: default`, but `ticket`/`request` stayed null so helper attach and spend join fail (G9, [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463)) | 🟡 partial: no gantt rows or spend (G9); rest untested (G18) |
| `agent-gantt` | 🟡 partial: hooks run in T3 sessions, pane in T3 not seen (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) |
| Ticket helper in the gantt | 🟢 works | 🔴 not supported: no gantt snapshot (G9) | 🟡 partial: WISE-441 helper filed CT-14; snapshots exist but `ticket`/`request` null (G9, G21, [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463), [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288)) | 🔴 not supported: no gantt snapshot (G9) |
| Security review subagent | 🟢 works | ⚪ untested (G4) | 🟡 partial: WISE-441 CT-7 posted Security review PASS on PR #13 from a Cursor dual-review path; MCP `readonly` enforcement still unchecked (G4) | ⚪ untested: no Antigravity branch in the skill (G4) |

Notes:

- Install links each skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and `~/.cursor/skills`, and each subagent into `~/.claude/agents` and `~/.cursor/agents`. It writes the instruction block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. It writes the same text to `~/.cursor/rules/collective-wisdom.mdc` for Cursor, with `alwaysApply: true`. It writes nothing for Antigravity.
- `install.sh` adds the Stop hook that runs the rotation check to `~/.claude/settings.json` and `~/.cursor/hooks.json`, and to no other harness. The Cursor hook has been tested only against Cursor's documented payload, and in Cursor's mode `none` it sends no `rotate:` line, but still sends `finish:` while a take over is unfinished and `late-child:` for a late child. `RESET_MODES` in `cos_rotation_check.py` and the Context reset row change together.
- `install.sh` also adds the Cursor gantt hook to `~/.cursor/hooks.json`, for six events. A Cursor thread on a worktree then gets gantt rows with timing, models, tokens and cost (G9). Like the Stop hook, it has not been seen running in a Cursor thread.
- The No Hands cost cap sums `agent_usage.py` over the run's tickets. A Cursor child is priced from its run store in `~/.cursor/projects`; a run on a model `prices.json` has no price for, or a store it cannot read, makes the ticket's cost unknown, and a No Hands run stops. A Codex or Antigravity child leaves nothing the script reads, so its cost is unknown and a No Hands run stops. Auto, which is all the Cursor routing since CW-275, is priced at the ceiling rate (WISE-442), so a Cursor ticket has a cost and counts toward the cap, at up to several times its real spend (G8).
- Antigravity appears as a provider in T3 Code, and the repo has nothing for it yet.
- Ticket helper in the gantt: the mod reads the ticket from the `TICKET HELPER DONE` block of a Claude Code helper's final answer (it needs the `agent-gantt` plugin at 0.1.11 or later), and the dashboard adds that session to the ticket's gantt and spend. On Linear and Jira the session reaches the ticket's chart once the ticket is in the Chief of Staff's saved list; see Matrix 2. A running helper with no ticket yet is a card in a Writing tickets section at the top of the Backlog tab, titled with the ticket description (plugin 0.1.14 or later) or, when the task has none, the request line. A finished helper that filed nothing leaves no card. The Cursor card has no title and stays until its turn ends, because the Cursor hook sets no `ticket` or `request` (G21).
- The Cursor column's Team skills load and Chief of Staff thread cells still rest in part on the 2026-11-09 run in [Runs](#runs). Ship loop, Install (G1), Subagents/Security review (G4), Local dashboard/gantt (G9), Usage (G8/G31), and Fresh-context reset (G28–G30) also rest on the 2026-11-15 WISE-441 run below (machine install at `400e8b6a`, rule file and Cursor hooks installed).
- Cursor model routing (WISE-441 / G31): (1) `.cursor/agents` files use `model: inherit`; CT-7 implementer and dual-review subagents ran on `cursor`/`default`. (2) Mid-thread `t3_thread_configure` for build is a no-op on Cursor because spec and build both route to `default`. (3) Gantt/run store rows recorded `model: default`. (4) `agent_usage.py --ticket CT-7` printed `cost unknown (no price for default; …)`, before WISE-442 priced Auto at the ceiling rate.
- Background waits (G32): WISE-441 saw `t3_background_wait` refuse on Cursor (`This provider cannot mark background work as awaited.`); shell background starts still work. Ticket: [#461](https://github.com/collective-wisdom-org/collective-wisdom/issues/461).
- Chief of Staff thread title (G33): WISE-441 `t3_thread_update` rename to `CT - Chief of Staff` succeeded.
- The Fresh-context reset row rests on the 2026-11-14 run in [Runs](#runs). It was a Claude Code run reported by the user; the build read no scratch thread. The row needs T3 Code after 0.1.9 with the notice fix, that is a nightly from 2026-11-13 or later until a stable release has it.

### Full compatibility

One line per column, saying what done means.

- **Claude Code in T3 Code:** done. A Chief of Staff and its children run a ticket from spec to merge, with subagents, the context reset and cost figures. The `agent-gantt` mod is the only open cell.
- **Codex in T3 Code:** done when a Chief of Staff and its children run a ticket to merge on Codex, with subagents, a context reset and cost figures that Codex can supply.
- **Cursor in T3 Code:** done when the instruction block installs without a manual paste, a Chief of Staff and its children run a ticket to merge on Cursor, with subagents, and the hook, a context reset and cost figures work for it.
- **Antigravity in T3 Code:** done when `install.sh` installs skills and the instruction block for it, a Chief of Staff and its children run a ticket to merge on it, with subagents, a security review, a context reset and cost figures.

## Matrix 2: trackers

Columns are the ticket trackers the `Tracker` row in `docs/agents/project.md` can name (GitHub Issues, Linear and Jira), plus Azure DevOps, which it cannot name yet.

| Feature | GitHub Issues | Linear | Jira | Azure DevOps (ADO) |
|---|---|---|---|---|
| Ticket operations (the adapter) | 🟢 works | 🟢 works (see note) | ⚪ untested: adapter never run (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Chief of Staff and ship loop | 🟢 works | 🟢 works (see note) | ⚪ untested (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Project manager hygiene and ranking | 🟢 works | 🟢 works | 🔴 not supported: `pm_hygiene.py` has no Jira shape; ranking untested (G13) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Untracked work check | 🟢 works | 🟡 partial: finds open PRs only (G14) | 🟡 partial: finds open PRs only (G14) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Dashboard issue links, titles and update order | 🟢 works | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) |
| Dashboard Todo and Backlog list | 🟢 works | 🟡 partial: read from the Chief of Staff's last Todo read and Backlog ranking, so it can lag the tracker (G22) | 🟡 partial: the same lag (G22); untested (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Ticket helper in the gantt | 🟢 works | 🟢 works: the session joins the ticket's row once the ticket is in the Chief of Staff's last saved list (G22) | ⚪ untested: same code as Linear (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Setup (`set up this repo`) | 🟢 works | 🟢 works | ⚪ untested: writes the Jira rows, never run against Jira (G12); a Data Center `_` key is refused (G24) | 🔴 not supported: no adapter in `trackers/` (G19) |
| PR flow and merge (needs GitHub for code) | 🟢 works | 🟢 works, code on GitHub | ⚪ untested, code on GitHub (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |

Notes:

- GitHub Issues: `trackers/github.md` says it was verified on 2026-11-03.
- Linear: `trackers/linear.md` has no verification line. Its `works` cells rest on the team running on Linear on one maintainer's machine, which is not a recorded verification; this covers every Linear `works` cell, not only the two marked. If you want `works` to mean a recorded verification like the GitHub adapter's, treat the Linear cells as `untested` (G16).
- Jira: `trackers/jira.md` is marked UNTESTED and its list of assumptions is unticked.
- Ticket helper in the gantt: a session joins a ticket's gantt when that ticket has a row on the board. A just-filed ticket gets its row from the Todo and Backlog list, which on Linear or Jira is the Chief of Staff's last saved list (G22), so the session reaches the ticket's chart once the ticket is in that list or in state. Spend does not depend on the board.
- Azure DevOps: here it means Azure Boards for tickets. The code stays on GitHub, as on every tracker. The repo has no mention of it outside an unrelated security checklist, so every cell is `not supported`.

### Full compatibility

- **GitHub Issues:** done. Every row works. The dashboard (its issue links, titles, update order and Todo and Backlog list) and the untracked check read issues, which only GitHub supports.
- **Linear:** done when the dashboard and the untracked check read Linear tickets as they read GitHub issues, including the Todo and Backlog list and the helper's chart, and `trackers/linear.md` carries a verification line.
- **Jira:** done when the `jira.md` checklist is ticked against a live site, `pm_hygiene.py` reads Jira's list shape, and the dashboard reads Jira tickets as it reads GitHub issues, including the Todo and Backlog list and the helper's chart.
- **Azure DevOps (ADO):** done when `trackers/` has an Azure DevOps adapter that the scripts read, verified against a live organization, and the dashboard and the untracked check read its work items.

## Recording a run

How to record a Chief of Staff run and a ship-loop child on a harness, so the matrix cells rest on a run and not a guess. Do it in a throwaway private repo, not in collective-wisdom: a second Chief of Staff there would fight the first over `.agent-team/state.json` and the Backlog.

1. Make a private GitHub repo with a one-line `README.md` and one small ticket, such as "Add a one-line project description to README.md". Leave out `docs/agents/project.md`: the thread under test has to set the repo up.
2. Clone it, add the clone as a T3 Code project, and start a thread with the harness under test.
3. Send `set up this repo` and answer its questions. Merge the setup PR it opens and have the thread pull the root checkout. Then send `start the team`. Take the ticket through spec, build and merge, approving the spec and the merge from that thread.
4. Open the dashboard for the repo and note the Chief of Staff tab: the thread's state and link.
5. Read the Chief of Staff thread and each child thread with `t3_thread_read`. Mark a cell `works` only on a quoted tool call or reply that shows it. Otherwise mark it `partial` or `not supported` with a reason.
6. File one ticket per failure and put its link on the cell's gap line. Fix nothing in the same ticket.
7. Add an entry under [Runs](#runs): date, harness, repo, thread ids, how far the ticket got, one line per cell.

A ship-loop child cannot start a thread on another harness, so step 2 is done by the user or the Chief of Staff.

## Runs

One entry per recorded run, newest first. The steps are in [Recording a run](#recording-a-run).

### 2026-11-15, Cursor Chief of Staff + fresh-context reset (WISE-441)

Recorded for [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441): a Cursor Chief of Staff on the trial repo with Cursor children, a Cursor ticket helper, and one hand fresh-context reset while work was still running. **Fix nothing** in this ticket; failures filed below.

- **T3 Code:** `0.1.10-nightly.20261114.4695` (`t3_environment_read` on the CoS thread).
- **Skills / install:** machine install at commit `400e8b6a3a60d3dd2d794c492937a4b8cfdd5b19` (WISE-459 Auto/`default` routing). `~/.cursor/rules/collective-wisdom.mdc` and Cursor hooks present.
- **Repo and tickets:** `dbeallor/cw-cursor-trial` (private), prefix `CT`. Code ticket CT-7 (PR [#13](https://github.com/dbeallor/cw-cursor-trial/pull/13)) taken through ship-loop on Cursor to `MERGE READY`. Specs CT-8/CT-9 reached `BUILD READY`. Docs ticket CT-4 (PR [#6](https://github.com/dbeallor/cw-cursor-trial/pull/6)) awaiting merge. Ticket helper filed CT-14.
- **Chief of Staff thread:** `d7a51255-d306-464d-bab9-5d94bc791db2` (provider `cursor`, model `default`). Title rename via `t3_thread_update` → `CT - Chief of Staff` (G33 works).
- **Harness consistency (selected rows):**

| Thread / role | Provider | Model | Source |
|---|---|---|---|
| CoS | cursor | default | `t3_thread_configure` |
| CT-7 child | cursor | default | `delegate_task` / `t3_thread_read` |
| Implement CT-7 ping.py | cursor | default | idle-check `sub` / `t3_thread_list` |
| CT-7 small dual review | cursor | default | idle-check `sub` |
| Ticket helper (CT-14) | cursor | default | `delegate_task` |
| Backlog ranking (take-over) | cursor | default | `delegate_task` |
| CT-8 / CT-9 children | cursor | default | `delegate_task` |
| CT-4 closeout / implement (earlier in trial) | cursor | composer-2.5-fast | progress harness table (flagged for G3) |

- **Install (G1): works.** CoS quoted `head -n 1 ~/.cursor/rules/collective-wisdom.mdc` → `---` before reading skill files.
- **Ship loop child threads (G3): partial.** CT-7 Cursor child reported `MERGE READY` with Code review PASS and Security review PASS on head `e89e6d0…`. Merge not completed at write-up time. Flagged row: earlier CT-4 path used `composer-2.5-fast`.
- **Subagents / security review (G4): partial.** CT-7 started implementer and dual-review subagents on Cursor Auto; security review PASS posted on PR #13. Whether `readonly: true` blocks MCP write tools was not proven.
- **Model routing (G31):**
  1. Subagent `model:`: `.cursor/agents/*.md` use `model: inherit`; subagents ran as `cursor`/`default` under the Auto parent. (CW-275's `auto-smart`/`optimize_for` expectation is obsolete after WISE-459.)
  2. Mid-thread configure: spec and build both route to `default`, so the build switch is a no-op on Cursor.
  3. Auto in the run store: gantt snapshots and usage paths record `model: default`.
  4. `agent_usage.py --ticket CT-7` → `cost unknown (no price for default; $0.00 priced), 1.7M tokens, …` (since WISE-442 this is a ceiling-rate dollar total, flagged on the line).
- **Local dashboard / gantt (G9): partial.** Dashboard started at `http://127.0.0.1:47236/`. Hooks wrote snapshots under `.agent-team/gantt/` and `gantt/cursor/`. Every inspected snapshot had `"ticket": null` and `"request": null` (helper that filed CT-14 included). Ticket: [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463) (also [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288)).
- **Background waits (G32): not supported.** `t3_background_wait` → `This provider cannot mark background work as awaited.` Ticket: [#461](https://github.com/collective-wisdom-org/collective-wisdom/issues/461).
- **Fresh-context reset (G28, G29, G30):** hand send `t3_thread_send` with `freshContext: true` and `CHIEF OF STAFF RESET 538743bd. Run /chief-of-staff take over.` while CT-7 and the ticket helper were still running. Mode stays `none` (no change to `RESET_MODES`).
  - (a) Same thread id: pass (`d7a51255-…`).
  - (b) New session: pass. Pre `chiefSessionId` `agent-5e57ba94-…` → post `agent-570c0144-…`; new transcript under `~/.cursor/projects/…/agent-transcripts/agent-570c0144-…`.
  - (c) Take over from state / skill whole: pass. Matched reset id; lean take-over restored CT-4/CT-7 and filled CT-8/CT-9.
  - (d) Finish notice across reset (G29): pass with late-child. Ticket helper completed at `23:18:17Z` (after reset send `23:18:13Z`). After take-over, Stop hook `late-child:` delivered CT-7/CT-8/CT-9 completions; CoS staged CT-7 to `awaiting-merge` and CT-8/CT-9 to `awaiting-build`.
  - (e) Context small (G30): fail / inconclusive. Pre-reset `cos_rotation_check.py` → `context=180k`. Post-reset `--record-takeover` → `size unknown`; `agent_usage.py --context` fails (`CLAUDE_CODE_SESSION_ID` unset). Ticket: [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462).
- **Tickets filed (failures only):** [#461](https://github.com/collective-wisdom-org/collective-wisdom/issues/461) (G32), [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462) (G30), [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463) (G9 attach).
- **Open at write-up:** CT-7 awaiting `approve 7` (merge); CT-4 awaiting `approve 4`; CT-8/CT-9 awaiting spec approval.

### 2026-11-14, fresh-context reset (CW-315)

Recorded for [#315](https://github.com/collective-wisdom-org/collective-wisdom/issues/315): whether the Chief of Staff thread can reset its own provider session with `freshContext: true` and keep working.

- **T3 Code:** `0.1.10-nightly.20261114.4695`, a nightly built on 2026-11-14, after the fix for pingdotgg/t3code issue 36087 (PR 36103) merged on 2026-11-13; the version was read with `t3_environment_read` on 2026-11-14, and the fix is inferred from the build date. All checks ran on it.
- **Scratch repo and thread:** `dbeallor/cw-scratch`, prefix `CS`, tickets CS-2 (PR #3), CS-4 (PR #6) and CS-5 (PR #7). Claude Code Chief of Staff thread `76c448b2-f998-4283-b874-adedd648944e`; its latest session at hand-back was `9cdeae2d`. No repo edits were made in `cw-scratch`.
- **What this rests on:** the user ran the checks in the scratch thread and reported the results in the CW-315 Chief of Staff thread on 2026-11-14, which the Chief of Staff relayed. The build did not read the scratch thread or its state, and the user's full notes file is outside the repo, so the lines below are the user's report, not quoted tool output. The build did the schema read in check 4 itself. Claude Code only.
- **1. Self-send with no children: pass for the reset, size unconfirmed.** New session in the same thread, `chiefSessionId` changed. Context 83,815 then 88,851 (+6%) as reported. The report does not say which turn each number is from, so the spec's within-25% comparison to a fresh thread's first take-over turn is not confirmed. If the numbers are before and after the reset, the reset did not shrink the context (G30).
- **2. Notice across the reset: pass as graded by the user, recovered by the idle check.** `BUILD READY` was handled by the new session through the take-over idle check and sweep. The report does not say the child's notice itself arrived in the new session, so notice delivery is not shown (G29).
- **3. Reset under load: pass, with a limit.**
  - (a) Two children across the reset: pass. CS-4 and CS-5 stayed tracked and running. CS-5's `MERGE READY` was lost across the reset and caught later by `cos_idle_check.py`, so this case shows the idle check recovering a lost notice, not delivery (G29).
  - (b) Reset during a merge wait: the first try was inconclusive because CS-2 merged before the reset. The retry passed: CS-4 merged after the reset and the notice path closed it out.
  - Limit: take-over step 4.2 starts no merge wait when the ticket's `parentThreadId` is the chief itself, so (b) shows the notice path, not a merge-wait wake. That path is untested, and the merge-wait wake needs a ticket under an older parent thread.
  - The direct send was accepted; the scheduled fallback was not needed.
- **4. Scripts after the reset: pass.** The report gives only "no import errors"; it does not say whether `cos_user_check.py` and `cos_approve_pr.py` found a pre-reset user message or that no script exited 2. The build read the schema on 2026-11-14 with `sqlite3 -readonly ~/.t3/userdata/statev2.sqlite '.schema <table>'`: every table and column the store-reading scripts select exists.
  - `orchestration_v2_projection_messages`: `message_id`, `thread_id`, `role`, `streaming`, `created_at`, `payload_json`.
  - `orchestration_v2_projection_threads`: `thread_id`, `project_id`, `title`, `default_provider`, `provider_instance_id`, `updated_at`, `archived_at`, `deleted_at`, `payload_json`.
  - `orchestration_v2_projection_runs`: `run_id`, `thread_id`, `ordinal`, `status`, `completed_at`.
  - `orchestration_v2_projection_turn_items`: `turn_item_id`, `thread_id`, `run_id`, `type`, `payload_json`.
  - `orchestration_v2_turn_item_positions`: `thread_id`, `turn_item_id`, `ordinal`.
  - `projection_projects`: `project_id`, `title`, `workspace_root`, `deleted_at` (read by `cos_peer.py`).
  - The JSON paths the scripts extract are present in current rows: `$.createdBy` and `$.text` on messages, `$.lineage.parentThreadId` and `$.lineage.relationshipToParent` on threads, `$.toolName` and `$.output` on `dynamic_tool` items, `$.text` and `$.streaming` on `assistant_message` items. Nothing is gone or renamed. The repo holds no earlier schema, so this is a check against what the scripts need, not a diff.
- **5. Stop hook and `chiefSessionId`: pass.** `chiefSessionId` matched the new session, and with a stale `skillCommit` set the `rotate:` line appeared once the 10-minute quiet window passed.
- **6. Queued `/compact`: partial.** After the compaction the `chief-of-staff` skill came back truncated mid-sentence in the Tick plan-line table (the cut text ends "Cleanup line, `Child read script u"), followed by "[... skill content truncated for compaction; use Read on the skill path ...]". The intro, reference table, Tools, Working set, Models, Lanes, State file and the start of Tick survive. The rest of the plan-line table, Child path, Guardrails and everything after are lost, so a chief must re-read `SKILL.md` after a compaction (G25). Since CW-329 the part of `SKILL.md` through § Guardrails (the plan-line table, § Child path and § Guardrails) fits in 18,000 bytes, under the 20,908 that survived here, and a size test in `test_agent_files.py` holds it there. That is not a live re-run of this check.
- **7. Codex and Cursor: not run.** The run covered Claude Code only. A Codex Chief of Staff starts no children while there is no routing table (CW-280, G2).
- **Other findings (not checks):**
  - A `freshContext` reset drops the test plan, so the plan has to live in state or a file.
  - A plain `take over` typed in the same session does not reset: context and `chiefSessionId` stay unchanged. Only `t3_thread_send` with `freshContext: true` resets.
  - A short `skillCommit` (`8ddace1`) is accepted but never matches. The check keeps printing "ok (skill change waits: relay Nm ago)", which reads as a pending rotation (G27).
  - `cos_state.py apply` rejects `lastRelayAt` as an "unknown top-level key", so testing the `rotate:` line means waiting out the quiet window. The Chief of Staff's read was that this is deliberate, because the relay path writes that key.
  - A 400 second background `sleep` once appeared to return at once. Probably a harness quirk, seen once, so no ticket.
- **Tickets:** [#328](https://github.com/collective-wisdom-org/collective-wisdom/issues/328) (reject a short `skillCommit`) and [#329](https://github.com/collective-wisdom-org/collective-wisdom/issues/329) (keep the Chief of Staff rules inside the compaction budget). Filed by the Chief of Staff, not by this build.
- **Open at hand-back:** CS-5 (PR #7) awaiting the user's `approve 5`; no children or merge waits running; `skillCommit` restored to the full 40-character sha.

### 2026-11-13, Claude Code in T3 Code (CW-280 control run)

The counterpart to the Cursor runs ([#256](https://github.com/collective-wisdom-org/collective-wisdom/issues/256), [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275)), recorded for [#280](https://github.com/collective-wisdom-org/collective-wisdom/issues/280): a Claude Code Chief of Staff should keep every child on Claude Code. This is a read of thread providers, not a full ship-loop run.

- **Repo and ticket:** collective-wisdom itself, running CW-280.
- **Skills:** the machine install while CW-280 was being built, before the harness-mismatch check shipped.
- **Chief of Staff thread:** `mcp:d9205ef0-5df4-4d79-8036-d25ef24f0888` reads `providerInstanceId` `claudeAgent`, model `claude-sonnet-5-5`.
- **Children and helpers: works.** The 40 newest threads (of 398 listed) were read with `t3_thread_list`. Eight have this Chief of Staff as parent, and all eight read `claudeAgent`:
  - Five ship-loop children: CW-280, CW-281, CW-284 and CW-286 on `claude-sonnet-5-5`, CW-288 on `claude-opus-5-5`.
  - One CW-290 child, on `claude-opus-5-5`.
  - Two ticket helpers, both on `claude-sonnet-5-5`: "helper gantt compat doc" and "Cursor helpers on ship loop".

  No child or helper was on another provider.
- **Not covered:**
  - No Backlog ranking or project manager hygiene child appeared in those 40 threads, so neither is checked.
  - The subagents inside the children (implementer, reviewers) were not read, so their provider is unchecked.
  - The count is as of the reading, before the mismatch check shipped. It shows a Claude Code Chief of Staff already kept its children on Claude Code. It does not show that the check catches a mismatch.
- **Touched, not settled:** the 358 threads outside the 40 newest were not read.

### 2026-11-09, Cursor in T3 Code (CW-256)

- **Repo and ticket:** `dbeallor/cw-cursor-trial` (private), ticket CT-1 "Add a one-line project description to README.md". The setup PR (#2) and the ticket PR (#3) both merged.
- **Skills:** the machine install at commit `070a3ca`, before CW-272 (Cursor model routing) and CW-258 (Cursor gantt hooks). `~/.cursor/rules/collective-wisdom.mdc` and `~/.cursor/hooks.json` were not installed on that machine, so the run used the skills only.
- **Threads:** the Cursor Chief of Staff is `62e3d411-af4d-43d6-b4f7-bef4a5683c79` (provider `cursor`, model `grok-4.7`, 17 runs). The CT-1 child is `thread:delegated-task:command%3Amcp%3Aae517946-635a-4eda-8195-fc8be9b29ee3%3Adelegate-task%3Aa4ae25e1-4b60-4aac-9b95-1e08a14a9e48` (provider `claudeAgent`, started on `claude-opus-5-5` for the spec, switched to `claude-sonnet-5-5` for build and merge). Three helper children were also `claudeAgent` on `claude-sonnet-5-5`: project manager hygiene (`…delegate-task%3Ab7405c24-b92e-4f5a-9fdb-331a5d22156d`) and two Backlog rankings (`…%3Aab1b4966-62cb-4d40-8ac0-dd87b9031309`, `…%3A338f3716-e78c-488b-a678-15381ae1f1c9`).
- **How far:** the user sent `set up this repo` (answering four questions, with a yes before each command), the thread opened setup PR #2, and the user merged it and asked the thread to pull the root checkout. Then the user sent `start the team`, `approve 1` on the spec and `approve 1` on the merge. CT-1 went from Backlog to merged PR #3 in 14 minutes of wall time. `agent_usage.py --ticket CT-1` put the CT-1 child's cost (spec, build and merge) at $1.26 API-equivalent. The three helper children (about $0.63 from their gantt snapshots) and the Chief of Staff's own cost are not in it (G8).
- **Team skills load: works.** The thread read `~/.cursor/skills/chief-of-staff/setup.md`, then `startup.md` and `SKILL.md` for `start the team`, and followed them (its own words: "Status is `set`. Continue with step 1: ensure-labels."). It found the skill by searching `~/.cursor/skills` and `~/.agents/skills` for "set up this repo"; there was no rule file to point it there.
- **Chief of Staff thread: works.** It ran `cos_state.py init`, `cos_tick.py --trigger start` and `delegate_task` for the CT-1 child. It relayed `BUILD READY` and `MERGE READY` to the user, checked each `approve 1` with `cos_user_check.py`, routed it with `cos_route.py`, and sent a `CHIEF OF STAFF:` relay with `t3_thread_send`. Before the merge relay it ran `cos_approve_pr.py CT-1`, which printed "cos-approve: verified approve 1 for #3 at f137b6d333a76936f6150e66d4f7878fe6091131". `cos_sweep.py` then found PR #3 merged. Three things came up:
  - The skills of that day told it to ask the user to switch the thread: "This thread is Grok 4.7, not Claude Sonnet 5.5 at medium effort. Switch this thread in T3 to Claude Sonnet 5.5, effort medium." CW-272 replaced that model table.
  - `cos_rotation_check.py` printed "ok (size unknown on Cursor)" (G8).
  - It recorded a first `lost-notice` sighting for CT-1 while the child's finish notice was still queued behind its turn (the notice run was requested at 04:47:38Z and started at 04:48:59Z). That looks like a queued notice, not a lost one. One sighting, so no ticket.
- **Ship loop child threads: partial.** Every child ran on Claude Code, because the Chief of Staff passed `providerInstanceId: "claudeAgent"` (the skills of that day). PR #3 has a code review comment ending "Verdict: PASS", a security review comment "Skipped: docs-only diff" ending "Verdict: PASS", a `## Docs check` comment, and `merge_pr.py` merged it. So a Cursor Chief of Staff drove a Claude Code child to `MERGED #3`. A Cursor child was not run (G3, [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275)). The child's finish notice began "My `status:done` label call failed, but the issue is already closed": no `status:done` label exists in the skills, scripts or tracker adapter, so the child made the call up. It ran on Claude Code and did no harm (the Chief of Staff confirmed the issue was closed), so no ticket for it.
- **Local dashboard: partial.** The dashboard API for the trial repo returned `chief` as `{"state":"idle","threadLink":"<t3-thread://v2/fa8d9b7c-8629-46cf-bc5f-096683c72719/62e3d411-af4d-43d6-b4f7-bef4a5683c79>"}` after the run, and CT-1 under `merged` with spend $1.26 and gantt rows for the children. The Cursor thread left no gantt snapshot: `.agent-team/gantt/` holds four files, all Claude Code sessions, which fits the Cursor hooks not being installed. The page itself was not opened and the link was not clicked; the API was read.
- **Touched, not settled:**
  - Install (G1): no rule file was installed, so the run neither shows nor rules out that a Cursor thread reads it.
  - Subagents (G4): the Cursor thread started none. The children's subagents (README edit, code review, docs check) ran on Claude Code.
  - Security review (G11): skipped as docs-only, so Cursor's `review-security` was not reached.
  - Stop hook: not installed on the machine, so not seen.
- **Tickets filed:** [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275) (run again with Cursor children), [#276](https://github.com/collective-wisdom-org/collective-wisdom/issues/276) (label colors, G20). [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273) cannot be answered from this run, because it ran before CW-272.

## Keeping it current

A PR that changes support for a cell updates that cell in the same PR. When a cell goes from not `works` to `works`, drop its gap and its reason. A cell moves to `works` only with the code, or a run the team does today, to show it.

A gap ticket links back to its cell here, by row, column and gap number. When the ticket exists, put its link on the gap's line below, in place of `none yet`.

## Gaps

One line per gap the matrices point at. A ticket is opened only where the maintainer wants one, so each line says `none yet` until it exists.

- **G1.** Settled by WISE-441: the Cursor CoS quoted `head -n 1 ~/.cursor/rules/collective-wisdom.mdc` → `---` before skill reads. Ticket: [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441).

- **G2.** No recorded Codex run in T3 Code: skills load, the Chief of Staff thread and the child threads are unchecked. Since CW-280 a Chief of Staff on Codex starts no children until a routing table exists. Ticket: none yet.
- **G3.** WISE-441 ran a Cursor ship-loop child (CT-7) to `MERGE READY` with code+security PASS; merge not in the write-up, and an earlier CT-4 path used `composer-2.5-fast`. Ticket: [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441).

- **G4.** WISE-441 started Cursor implementer and dual-review subagents (`model: inherit` → `default`) and posted a Security review PASS on CT-7 PR #13. Whether `readonly` blocks MCP write tools is still unchecked. Codex/Antigravity still untested. Ticket: none yet.

- **G5 and G6** are retired. Their numbers are not reused.
- **G7.** The Stop hook that runs the rotation check is installed for Claude Code and Cursor only. Codex and Antigravity get no hook, and no reset mode (`none`). Ticket: none yet.
- **G8.** `agent_usage.py` reads `~/.claude/projects` transcripts and Cursor's `~/.cursor/projects` run stores, so the cost report and the No Hands cost cap do not see Codex or Antigravity work, and a Cursor run on a model with no price in `prices.json` (Grok 4.6, Gemini), or a Cursor store that cannot be read, shows `cost unknown`. Auto (`default`) bills at the list price of the model each request is routed to, and the run store does not name that model (WISE-441), so `prices.json` has a `default` row at the highest rate of each token kind, kept at or above every other row by `test_prices.py` (WISE-442). The `--ticket` line adds `(Auto at the ceiling rate)` after `Cursor $Y` when a run was on Auto; the gantt and dashboard show the same dollars with no mark. The ceiling is never below a model the team prices and can run several times above the real bill (on a WISE-441 run, about $0.77 against $0.10 at Composer 2.5's rate), so a No Hands run under a Cursor Chief of Staff reaches its cap sooner than its real spend, a safe direction. Cursor's Teams and Enterprise token rate is not added. `grok-4.7` and `composer-2.5` stay priced (CW-272) at the standard rate: a Grok prompt of 200K or more and Fast mode cost more than the report shows. `--context` still reads Claude Code only, but the rotation check reads a Cursor Chief of Staff's context size from its run store (CW-341): the latest turn's `inputTokens` (a sum over the turn's model requests) divided by the request count, taken from the distinct `call-<uuid>` prefixes of the turn's `tool_call` ids. That average is a floor on the last prompt, so on the checked run the size can trigger late on a long turn and never early (a request that leaves no `tool_call` event would raise the average); the `call_id` format is not documented by Cursor and was checked on one `grok-4.7` run. Its reset mode stays `none`, so the size shows in the line (`ok (no reset on cursor; context=<N>k)`) but there is no size trigger and no skill-change reset. Ticket: none yet.
- **G9.** WISE-441: Cursor hooks wrote gantt snapshots (timing + `model: default`), but every inspected snapshot kept `ticket`/`request` null, so the helper that filed CT-14 did not attach. Ticket: [#463](https://github.com/collective-wisdom-org/collective-wisdom/issues/463) (also [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288)).

- **G10.** `agent-gantt` is a Claude Code plugin, so Codex, Cursor and Antigravity threads do not run it, and whether T3 Code shows its pane for Claude Code is unchecked. Ticket: none yet.
- **G11** is resolved by CW-254. The `security-review` skill now has a Cursor child start a general subagent with `security-review.md` as its prompt, and ignore an installed `review-security` in the ship loop. No Cursor run is recorded yet (G4).
- **G12.** Jira has never been run: the adapter is marked UNTESTED and its checklist is unticked. Ticket: none yet.
- **G13.** `pm_hygiene.py` parses the Linear and GitHub list shapes, not Jira's. Ticket: none yet.
- **G14.** The untracked work check reads `agent`-labelled issues only for GitHub. On Linear and Jira it finds untracked work from open PRs alone. Ticket: none yet.
- **G15.** The dashboard's issue links, issue titles and update order call `gh issue` and are on only for GitHub. Ticket: none yet.
- **G16.** The Linear adapter has no verification line. Ticket: none yet.
- **G17.** `install.sh` writes nothing for Antigravity, neither skills nor the instruction block. Ticket: none yet.
- **G18.** No recorded Antigravity run in T3 Code: skills load, the Chief of Staff thread and the child threads, and the dashboard's Chief of Staff state are unchecked. Since CW-280 a Chief of Staff on Antigravity starts no children until a routing table exists. Ticket: none yet.
- **G19.** There is no Azure DevOps adapter: `trackers/` has GitHub, Linear and Jira only, and the `Tracker` row in `project.md` cannot name it. Ticket: none yet.
- **G20.** `trackers/github.md` § `ensure-labels` names the team labels but not their colors or descriptions, so the Cursor Chief of Staff in the 2026-11-09 run copied them from the collective-wisdom repo. The same step on the other harnesses is not recorded. No matrix cell points at it: it came from the 2026-11-09 run. Ticket: [#276](https://github.com/collective-wisdom-org/collective-wisdom/issues/276).
- **G21.** The Cursor gantt hook (`cursor_gantt_hook.ts` via `mods/agent-gantt/hooks/cursor.ts`) writes no `ticket` or `request`, so a Cursor helper's card has no title, stays until its turn ends, and its session never joins the ticket it filed or that ticket's spend. No Cursor hook run is recorded (see G9). Ticket: [#288](https://github.com/collective-wisdom-org/collective-wisdom/issues/288).
- **G22.** On Linear and Jira the dashboard's Todo and Backlog lists come from `.agent-team/tracker-lists.json`, which the Chief of Staff writes: the Todo list on each turn that reads Todo (a free spec slot) and the Backlog list after each ranking. Between reads the lists can lag the tracker. A fresher list would need a tracker read on every turn. Issue: [#298](https://github.com/collective-wisdom-org/collective-wisdom/issues/298).
- **G24.** A Jira Data Center site whose admin allows `_` in project keys cannot use the team: `project_config.py`, `setup_repo.py`, the dashboard and the `agent-gantt` mod read a ticket prefix as letters and digits only. Jira Cloud does not allow `_` in a key. It hangs on the Jira column's Setup row. Ticket: none yet.
- **G25.** A queued `/compact` truncates the `chief-of-staff` skill (check 6 of the 2026-11-14 run): the skill comes back cut mid-sentence in the Tick plan-line table, so a `/compact` did not replace a reset by itself, since a chief had to re-read `SKILL.md` first. CW-329 moved text out so the core (through § Guardrails) fits in 18,000 bytes, under the 20,908 that survived, and a size test holds it there. It has not been re-run live. Ticket: [#329](https://github.com/collective-wisdom-org/collective-wisdom/issues/329).
- **G26** is retired. Its number is not reused. Its test needed a ticket under a retired Chief of Staff thread, and since CW-317 none can exist.
- **G27.** The state file accepts a short `skillCommit` (`8ddace1` in the 2026-11-14 run) that never matches the skill's commit, and the rotation check keeps printing "ok (skill change waits: relay Nm ago)", which reads as a pending rotation. No matrix cell points at it: it came from the 2026-11-14 run. Ticket: [#328](https://github.com/collective-wisdom-org/collective-wisdom/issues/328).
- **G28.** WISE-441 recorded a Cursor hand reset (`freshContext: true`, id `538743bd`): same thread id, new `chiefSessionId`/transcript, take-over from state. Mode stays `none` (no auto rotate). Codex still untested. Ticket: [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441).

- **G29.** WISE-441: ticket helper completed across the reset; after take-over, Cursor Stop-hook `late-child:` delivered CT-7/CT-8/CT-9 completions to the new session. Ticket: [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441).

- **G30.** WISE-441 could not read post-reset context on Cursor (`size unknown`; `agent_usage.py --context` needs `CLAUDE_CODE_SESSION_ID`). Pre-reset showed `context=180k`. Ticket: [#462](https://github.com/collective-wisdom-org/collective-wisdom/issues/462).
- **G31.** Cursor Auto routing checks from the CW-275 follow-up / WISE-441: subagent `model: inherit` under Auto, mid-thread configure no-op when both roles are `default`, store records `default`, `agent_usage.py --ticket` printed cost unknown for `default` (priced at the ceiling rate since WISE-442, G8). Ticket: [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441).
- **G32.** Cursor `t3_background_wait` is not supported (`This provider cannot mark background work as awaited.`). Shell background starts still work. Ticket: [#461](https://github.com/collective-wisdom-org/collective-wisdom/issues/461).
- **G33.** Cursor has `t3_thread_update`; WISE-441 renamed the CoS thread successfully. Ticket: none (works).
