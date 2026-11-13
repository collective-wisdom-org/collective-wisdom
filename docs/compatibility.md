# Compatibility

What the agent team does on each harness and each ticket tracker, and where it does not. Read this before you adopt the team on a setup other than Claude Code in T3 Code with GitHub Issues. It is this repo's own page and is not shipped to apps.

Last checked against the code and the 2026-11-09 Cursor run on 2026-11-09.

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
| Install (skills and instruction block) | 🟢 works | 🟢 works | 🟡 partial: rule file written, no Cursor thread seen reading it (G1) | 🔴 not supported: `install.sh` writes nothing for it (G17) |
| Team skills load | 🟢 works | ⚪ untested (G2) | 🟢 works | ⚪ untested (G18) |
| Subagents | 🟢 works | ⚪ untested: role file as prompt (G4) | 🟡 partial: Cursor-valid copies installed, no Cursor run recorded (G4) | ⚪ untested: role file as prompt (G4) |
| Chief of Staff thread | 🟢 works | ⚪ untested (G2) | 🟢 works | ⚪ untested (G18) |
| Ship loop child threads | 🟢 works | ⚪ untested (G2) | 🟡 partial: a Cursor Chief of Staff drove Claude Code children to merge, no Cursor child run (G3) | ⚪ untested (G18) |
| Stop hook (thread rotation) | 🟢 works | 🔴 not supported: hook installed for Claude Code and Cursor only (G7) | 🟡 partial: skill-change rotation only, no size trigger (G8) | 🔴 not supported: hook installed for Claude Code and Cursor only (G7) |
| Usage and cost report | 🟢 works | 🔴 not supported: reads Claude Code and Cursor runs only (G8) | 🟡 partial: models outside the routing show cost unknown, and Grok long prompts and Fast mode are priced at the standard rate (G8) | 🔴 not supported: reads Claude Code and Cursor runs only (G8) |
| Local dashboard | 🟢 works | 🟡 partial: no gantt rows or spend (G9) | 🟡 partial: the Chief of Staff tab data shows the Cursor thread's state and link; no gantt row or spend for that thread in the run (G9) | 🟡 partial: no gantt rows or spend (G9); rest untested (G18) |
| `agent-gantt` | 🟡 partial: hooks run in T3 sessions, pane in T3 not seen (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) |
| `status-pane` | ⚪ untested: pane in T3 not seen (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) | 🔴 not supported: Claude Code plugin (G10) |
| Security review subagent | 🟢 works | ⚪ untested (G4) | ⚪ untested: role file as prompt (G4) | ⚪ untested: no Antigravity branch in the skill (G4) |

Notes:

- Install links each skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and `~/.cursor/skills`, and each subagent into `~/.claude/agents` and `~/.cursor/agents`. It writes the instruction block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. It writes the same text to `~/.cursor/rules/collective-wisdom.mdc` for Cursor, with `alwaysApply: true`. It writes nothing for Antigravity.
- `install.sh` adds the rotation Stop hook to `~/.claude/settings.json` and `~/.cursor/hooks.json`, and to no other harness. The Cursor hook has been tested only against Cursor's documented payload. It becomes `works` once a Cursor Chief of Staff thread has run it.
- `install.sh` also adds the Cursor gantt hook to `~/.cursor/hooks.json`, for six events. A Cursor thread on a worktree then gets gantt rows with timing and models, but no tokens or spend (G9). Like the rotation hook, it has not been seen running in a Cursor thread.
- The No Hands cost cap sums `agent_usage.py` over the run's tickets. A Cursor child is priced from its run store in `~/.cursor/projects`; a run on a model `prices.json` has no price for, or a store it cannot read, makes the ticket's cost unknown, and a No Hands run stops. A Codex or Antigravity child leaves nothing the script reads, so its cost is unknown and a No Hands run stops.
- Antigravity appears as a provider in T3 Code, and the repo has nothing for it yet.
- The Cursor column's Team skills load, Chief of Staff thread, Ship loop and Local dashboard cells rest on the 2026-11-09 run in [Runs](#runs). That run used the skills only: the Cursor rule file and Cursor hooks were not installed on its machine.

### Full compatibility

One line per column, saying what done means.

- **Claude Code in T3 Code:** done. A Chief of Staff and its children run a ticket from spec to merge, with subagents, the rotation hook and cost figures. The two mods are the only open cells.
- **Codex in T3 Code:** done when a Chief of Staff and its children run a ticket to merge on Codex, with subagents, a rotation hook and cost figures that Codex can supply.
- **Cursor in T3 Code:** done when the instruction block installs without a manual paste, a Chief of Staff and its children run a ticket to merge on Cursor, with subagents, and the hook and cost figures work for it.
- **Antigravity in T3 Code:** done when `install.sh` installs skills and the instruction block for it, a Chief of Staff and its children run a ticket to merge on it, with subagents, a security review, a rotation hook and cost figures.

## Matrix 2: trackers

Columns are the ticket trackers the `Tracker` row in `docs/agents/project.md` can name (GitHub Issues, Linear and Jira), plus Azure DevOps, which it cannot name yet.

| Feature | GitHub Issues | Linear | Jira | Azure DevOps (ADO) |
|---|---|---|---|---|
| Ticket operations (the adapter) | 🟢 works | 🟢 works (see note) | ⚪ untested: adapter never run (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Chief of Staff and ship loop | 🟢 works | 🟢 works (see note) | ⚪ untested (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Project manager hygiene and ranking | 🟢 works | 🟢 works | 🔴 not supported: `pm_hygiene.py` has no Jira shape; ranking untested (G13) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Untracked work check | 🟢 works | 🟡 partial: finds open PRs only (G14) | 🟡 partial: finds open PRs only (G14) | 🔴 not supported: no adapter in `trackers/` (G19) |
| Dashboard issue links, titles and update order | 🟢 works | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) | 🔴 not supported: GitHub only (G15) |
| Setup (`set up this repo`) | 🟢 works | 🟢 works | ⚪ untested: writes the Jira rows, never run against Jira (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |
| PR flow and merge (needs GitHub for code) | 🟢 works | 🟢 works, code on GitHub | ⚪ untested, code on GitHub (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |

Notes:

- GitHub Issues: `trackers/github.md` says it was verified on 2026-11-03.
- Linear: `trackers/linear.md` has no verification line. Its `works` cells rest on the team running on Linear on one maintainer's machine, which is not a recorded verification; this covers every Linear `works` cell, not only the two marked. If you want `works` to mean a recorded verification like the GitHub adapter's, treat the Linear cells as `untested` (G16).
- Jira: `trackers/jira.md` is marked UNTESTED and its list of assumptions is unticked.
- Azure DevOps: here it means Azure Boards for tickets. The code stays on GitHub, as on every tracker. The repo has no mention of it outside an unrelated security checklist, so every cell is `not supported`.

### Full compatibility

- **GitHub Issues:** done. Every row works. The dashboard and the untracked check read issues, which only GitHub supports.
- **Linear:** done when the dashboard and the untracked check read Linear tickets as they read GitHub issues, and `trackers/linear.md` carries a verification line.
- **Jira:** done when the `jira.md` checklist is ticked against a live site, and `pm_hygiene.py` reads Jira's list shape.
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

- **G1.** `install.sh` writes the instruction block to `~/.cursor/rules/collective-wisdom.mdc`, but no Cursor thread in T3 Code is recorded reading it. The 2026-11-09 run had no rule file installed, so it settles nothing here. The next Cursor run checks it. Ticket: [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275).
- **G2.** No recorded Codex run in T3 Code: skills load, the Chief of Staff thread and the child threads are unchecked. Ticket: none yet.
- **G3.** No recorded Cursor ship-loop child. In the 2026-11-09 run ([Runs](#runs)) the Cursor Chief of Staff, on skills from before CW-272, started every child on Claude Code. Whether a Cursor child runs the ship loop to merge is unchecked. Ticket: [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275).
- **G4.** Subagents are proven only in Claude Code. Per Cursor's docs, Cursor loads Cursor-valid copies from `~/.cursor/agents`, but no Cursor run is recorded: the Cursor agent CLI was not logged in. Whether `readonly` also stops a reviewer's MCP write tools is unchecked. `AGENTS.md` says other hosts start a general subagent with the role file as its prompt, so Codex and Antigravity still work that way, and nobody has recorded doing it. The `security-review` skill has no Antigravity branch, so its security review runs the same way there. Ticket: none yet.
- **G5 and G6** are retired. Their numbers are not reused.
- **G7.** The rotation Stop hook is installed for Claude Code and Cursor only. Codex and Antigravity get no hook. Ticket: none yet.
- **G8.** `agent_usage.py` reads `~/.claude/projects` transcripts and Cursor's `~/.cursor/projects` run stores, so the cost report and the No Hands cost cap do not see Codex or Antigravity work, and a Cursor run on a model with no price in `prices.json` (Auto, Grok 4.6, Gemini), or a Cursor store that cannot be read, shows `cost unknown`. The Cursor routing models `grok-4.7` and `composer-2.5` are priced (CW-272) at the standard rate: a Grok prompt of 200K or more and Fast mode cost more than the report shows. `--context` still reads Claude Code only, so a Cursor Chief of Staff has no context size and its rotation hook rotates only on a skill change. Ticket: none yet.
- **G9.** The dashboard's gantt rows and spend come from `agent-gantt` snapshots. Cursor threads write them through Cursor hooks (CW-258), with timing and models but no tokens or cost, because Cursor's hooks and transcripts carry none. Codex and Antigravity threads still write none. The 2026-11-09 run left no snapshot for the Cursor Chief of Staff thread, with the Cursor hooks not installed on its machine, so whether the hooks write one is unchecked; the next Cursor run checks it. Ticket: [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275).
- **G10.** `agent-gantt` and `status-pane` are Claude Code plugins, so Codex, Cursor and Antigravity threads do not run them, and whether T3 Code shows their panes for Claude Code is unchecked. Ticket: none yet.
- **G11** is resolved by CW-254. The `security-review` skill now has a Cursor child start a general subagent with `security-review.md` as its prompt, and ignore an installed `review-security` in the ship loop. No Cursor run is recorded yet (G4).
- **G12.** Jira has never been run: the adapter is marked UNTESTED and its checklist is unticked. Ticket: none yet.
- **G13.** `pm_hygiene.py` parses the Linear and GitHub list shapes, not Jira's. Ticket: none yet.
- **G14.** The untracked work check reads `agent`-labelled issues only for GitHub. On Linear and Jira it finds untracked work from open PRs alone. Ticket: none yet.
- **G15.** The dashboard's issue links, issue titles and update order call `gh issue` and are on only for GitHub. Ticket: none yet.
- **G16.** The Linear adapter has no verification line. Ticket: none yet.
- **G17.** `install.sh` writes nothing for Antigravity, neither skills nor the instruction block. Ticket: none yet.
- **G18.** No recorded Antigravity run in T3 Code: skills load, the Chief of Staff thread and the child threads, and the dashboard's Chief of Staff state are unchecked. Ticket: none yet.
- **G19.** There is no Azure DevOps adapter: `trackers/` has GitHub, Linear and Jira only, and the `Tracker` row in `project.md` cannot name it. Ticket: none yet.
- **G20.** `trackers/github.md` § `ensure-labels` names the team labels but not their colors or descriptions, so the Cursor Chief of Staff in the 2026-11-09 run copied them from the collective-wisdom repo. The same step on the other harnesses is not recorded. No matrix cell points at it: it came from the 2026-11-09 run. Ticket: [#276](https://github.com/collective-wisdom-org/collective-wisdom/issues/276).
