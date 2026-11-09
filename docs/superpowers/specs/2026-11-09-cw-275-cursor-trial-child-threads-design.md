# CW-275: Run the Cursor trial again with Cursor child threads and record the ship loop cell

**Status:** Draft
**Ticket:** [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275)

## Goal

Find out whether a ship-loop child running on Cursor takes a ticket to `MERGED #N`, now that CW-272 routes a Cursor Chief of Staff's children to Cursor models. Record the run in `docs/compatibility.md` § Runs, set the Ship loop child threads cell on the Cursor column, and say what the run showed for the rule file (G1) and the Cursor gantt hooks (G9).

## Today

Facts from `main` at `304891f` and the machine, read 2026-11-09.

- `docs/compatibility.md` on `main` has no `## Recording a run` or `## Runs` section, and the Cursor cells still read `untested (G3)`. Both sections, the CW-256 run entry and the `partial` Ship loop cell come from PR #277 (CW-256), which is open and not merged. This ticket edits text that PR adds.
- The machine install (`~/.collective-wisdom`) points at the root checkout, at `304891f`: it includes CW-272 (Cursor model routing) and CW-258 (Cursor gantt hooks).
- `install.sh` has been run with those skills: `~/.cursor/rules/collective-wisdom.mdc` exists, `~/.cursor/hooks.json` holds the `cursor_gantt_hook.ts` entries and the `cos_rotation_check.py --hook` stop hook, and `~/.cursor/agents/*.md` pin `grok-4.7` (code-reviewer, security-reviewer) and `composer-2.5` (implementer, documenter, compacter).
- `dbeallor/cw-cursor-trial` exists with issue #1 (CT-1, closed) and PRs #2 and #3 (merged). It already has `docs/agents/project.md` from the CW-256 run. No local clone of it is on the machine any more.
- `chief-of-staff/SKILL.md` § Models `### Cursor`: a Chief of Staff whose own provider is `cursor` starts the spec child on `grok-4.7` and switches it to `composer-2.5` for build and merge; helper children run on `composer-2.5`.

## The run

A ship-loop child cannot start a Cursor thread (its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`), so the user starts it, as in CW-256. The build stops once with `BLOCKED: Cursor run needed` and picks up when the Chief of Staff relays that the run is done.

### Build steps

1. **Wait for #277.** This ticket edits the `## Runs` entry, the Ship loop cell, G1, G3 and G9 that PR #277 writes. If #277 has not merged when the build starts, stop with `BLOCKED: waiting on #277`. Once it has, merge `origin/main` into this branch.
2. **Machine check.** Confirm the install is current: `git -C ~/.collective-wisdom rev-parse HEAD` is at or after `304891f`, and the rule file, hooks and agent files above are in place. Record the commit. If any is missing, stop with `BLOCKED:` and ask the user to run `./install.sh` from the root checkout; the child does not run it (it writes to `$HOME` and links the root checkout).
3. **Trial ticket.** File one new issue in `dbeallor/cw-cursor-trial` with `~/.collective-wisdom/scripts/gh.sh issue create -R dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker", type Improvement, one sentence of scope. It gets the next issue number, so its id is `CT-4`. Give it the labels the trial repo's tracker adapter needs to be ready for the team (the ones CT-1 had).
4. **Hand-off.** Stop with `BLOCKED: Cursor run needed` and these steps for the user:
   1. Clone `dbeallor/cw-cursor-trial` to `~/Documents/git/cw-cursor-trial` (or pull an existing clone to `main`) and add it as a T3 Code project if it is not one.
   2. In that project start a new thread with the Cursor provider, model `composer-2.5`, fast mode off (the Chief of Staff model in § Models Cursor).
   3. Before `start the team`, send: `Quote the first line of your collective-wisdom rule, and say where it came from.` This is the G1 check.
   4. Send `start the team`. Approve the spec and the merge for CT-4 from that thread when it asks. Do not tell it which provider to give the child.
   5. Reply here with `CHIEF OF STAFF:` and the Cursor Chief of Staff thread id and how far CT-4 got. The child thread ids are read from the threads.
5. **Read the run.** With `t3_thread_read`, read the Cursor Chief of Staff thread and each child it started. For each check below, record the result from a quoted tool call or reply, not a guess.
6. **Files and stores.** Read the trial root checkout's `.agent-team/state.json` and `.agent-team/gantt/`, run the dashboard API for the trial repo (`agent-team/scripts/dashboard/server.ts`, `/api`), and run `agent_usage.py --ticket CT-4` from the trial clone. Read the trial PR's comments with `gh.sh`.
7. **Tickets.** File one ticket in collective-wisdom per failure with the `write-ticket` skill, linking its cell and gap. Fix nothing.
8. **Doc.** Edit `docs/compatibility.md`: a new Runs entry above the CW-256 one, the Ship loop child threads cell, G1, G3, G9, the Install cell, and the Local dashboard cell if the run settles it. Update the "Last checked" line. Then open the PR.

### What the run checks

| Check | Works when |
|---|---|
| Child provider | The Chief of Staff's `delegate_task` for CT-4 passes `providerInstanceId: "cursor"` and model `grok-4.7`, and the child thread's provider reads `cursor` |
| Ship loop child threads | The Cursor child runs ship-loop to `MERGED #N`: spec pushed and `BUILD READY`, PR opened, a code review comment and a security review comment ending `Verdict: PASS` (a docs-only skip counts if the comment says so), a `## Docs check` comment, and `merge_pr.py` merges |
| Mid-thread switch | `t3_thread_configure` moves the child to `composer-2.5` before the spec-approval relay, and the child's later turns run on it |
| G1, rule file | The thread quotes the rule file's first line and names `collective-wisdom.mdc` or Cursor rules as the source, before any skill file is read |
| G9, gantt | `.agent-team/gantt/` in the trial root checkout holds a snapshot for the Cursor Chief of Staff thread, and the dashboard API shows a gantt row for it |

The run also records the evidence #273 asks for: the model ids in each child's and subagent's run store, the fast mode setting where the store shows it, and the `agent_usage.py --ticket CT-4` output. Recording it here means #273 needs no second run; its own doc and skill edits stay in #273.

Cells the run touches but the ticket does not ask about (Subagents G4, Security review G11, Stop hook, Usage and cost report) get a note in the entry when the run shows something, and keep their value unless the run settles them.

### Ship loop cell result

- `works` when every Ship loop check above holds and the child's provider is `cursor`. G3 is then dropped, per `## Keeping it current`.
- Otherwise `partial` or `not supported`, saying what broke, with a ticket link on G3.

## Calls I made (surprising first)

- **The build waits on PR #277 and stops if it has not merged.** This ticket edits the Runs entry and cells that PR adds; starting from `main` without it would fork the doc.
- **The build stops halfway for you to start the Cursor thread**, as CW-256 did. That `BLOCKED:` is planned.
- **You start the Chief of Staff thread on `composer-2.5`, fast mode off**, the model § Models Cursor names for it, so the run tests the routing as written.
- **G1 is tested with one question before `start the team`**: ask the thread to quote the rule. A thread that only finds the skills by searching would not know the rule's first line.
- **The child files trial ticket CT-4** in `dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker". Docs-only, so the security review may skip; the cell accepts a skip comment that ends `Verdict: PASS`.
- **The trial clone goes to `~/Documents/git/cw-cursor-trial`**, next to the other repos; the CW-256 clone at `~/Documents/cw-cursor-trial` is gone.
- **The child does not run `install.sh`.** The machine install is already current; if it is not, the run stops and asks you.
- **#273's evidence is recorded in this run's entry, but #273's own edits stay in #273.**
- **No new gap number.** Failures go on G1, G3 and G9; a new gap only if the run finds something no gap covers.

## Leaves out

- Fixing anything that fails (one ticket each).
- Codex and Antigravity runs.
- The `chief-of-staff` § Models "not yet observed" note and G8 edits (#273).
- Any change to skills, scripts or `install.sh`.
- Deleting the trial repo or the clone.

## Touches

None of: data, money, auth, user email, migrations. It files one issue in the private trial repo, and the run merges one PR there.
