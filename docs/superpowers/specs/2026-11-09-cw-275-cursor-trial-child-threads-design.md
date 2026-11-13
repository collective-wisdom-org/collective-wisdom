# CW-275: Run the Cursor trial again with Cursor child threads and record the ship loop cell

**Status:** Draft
**Ticket:** [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275) (also covers [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273), closed as a duplicate)

## Goal

Find out whether a ship-loop child running on Cursor takes a ticket to `MERGED #N`, now that CW-272 routes a Cursor Chief of Staff's children to Cursor models, and whether that routing holds up in a real run. Record the run in `docs/compatibility.md` § Runs, set the Ship loop child threads cell on the Cursor column, say what the run showed for the rule file (G1) and the Cursor gantt hooks (G9), and give each of the four routing checks from #273 a result:

1. Does a Cursor subagent run on the model named by `model:` in `agent-team/.cursor/agents/<name>.md`?
2. Does `t3_thread_configure` switch a Cursor child to a new model partway through a thread?
3. Does the Cursor run store tell a Fast mode run apart from a standard one, so the cost report does not show too little?
4. Does `agent_usage.py --ticket` price a real run on each routed model?

Then replace the "Not yet observed" paragraph in `chief-of-staff/SKILL.md` § Models `### Cursor` with what was observed.

## Today

Facts from `main` at `304891f` and the machine, read 2026-11-09.

- `docs/compatibility.md` on `main` has no `## Recording a run` or `## Runs` section, and the Cursor cells still read `untested (G3)`. Both sections, the CW-256 run entry and the `partial` Ship loop cell come from PR #277 (CW-256), which is open and not merged. This ticket edits text that PR adds.
- The machine install (`~/.collective-wisdom`) points at the root checkout, at `304891f`: it includes CW-272 (Cursor model routing) and CW-258 (Cursor gantt hooks).
- `install.sh` has been run with those skills: `~/.cursor/rules/collective-wisdom.mdc` exists, `~/.cursor/hooks.json` holds the `cursor_gantt_hook.ts` entries and the `cos_rotation_check.py --hook` stop hook, and `~/.cursor/agents/*.md` pin `grok-4.7` (code-reviewer, security-reviewer) and `composer-2.5` (implementer, documenter, compacter).
- `dbeallor/cw-cursor-trial` exists with issue #1 (CT-1, closed) and PRs #2 and #3 (merged). It already has `docs/agents/project.md` from the CW-256 run. No local clone of it is on the machine any more.
- `chief-of-staff/SKILL.md` § Models `### Cursor`: a Chief of Staff whose own provider is `cursor` starts the spec child on `grok-4.7` and switches it to `composer-2.5` for build and merge; helper children run on `composer-2.5`. The section ends with "Not yet observed (CW-256)", listing checks 1 to 3 as open.
- `docs/compatibility.md` on `main`: the Usage and cost report row's Cursor cell says Grok long prompts and Fast mode are priced at the standard rate (G8), and G8 says the same.
- The CW-256 run cannot answer the routing checks: it ran on skills from before CW-272, and no Cursor child or Cursor subagent ran.

## The run

A ship-loop child cannot start a Cursor thread (its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`), so the user starts it, as in CW-256. The build stops once for the user with `BLOCKED: Cursor run needed` and picks up when the Chief of Staff relays that the run and its top-up are done. The ticket changes markdown files only (the doc and one skill paragraph), so the build works from this spec and writes no plan.

### Build steps

1. **Wait for #277.** This ticket edits the `## Runs` entry, the Ship loop cell, G1, G3 and G9 that PR #277 writes. If #277 has not merged when the build starts, stop with `BLOCKED: waiting on #277`. Once it has, merge `origin/main` into this branch.
2. **Machine check.** Confirm the install is current: `git -C ~/.collective-wisdom rev-parse HEAD` is at or after `304891f`, and the rule file, hooks and agent files above are in place. Record the commit. If any is missing, stop with `BLOCKED:` and ask the user to run `./install.sh` from the root checkout; the child does not run it (it writes to `$HOME` and links the root checkout).
3. **Trial ticket.** File one new issue in `dbeallor/cw-cursor-trial` with `~/.collective-wisdom/scripts/gh.sh issue create -R dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker", type Improvement, one sentence of scope. It gets the next issue number, so its id is `CT-4`. Give it the labels the trial repo's tracker adapter needs to be ready for the team (the ones CT-1 had).
4. **Hand-off.** Stop with `BLOCKED: Cursor run needed` and these steps for the user:
   1. Clone `dbeallor/cw-cursor-trial` to `~/Documents/git/cw-cursor-trial` (or pull an existing clone to `main`) and add it as a T3 Code project if it is not one.
   2. In that project start a new thread with the Cursor provider, model `composer-2.5`, Fast mode off (the Chief of Staff model in § Models Cursor).
   3. Before `start the team`, send: `Quote the first line of your collective-wisdom rule, and say where it came from.` This is the G1 check.
   4. Send `start the team`. Approve the spec and the merge for CT-4 from that thread when it asks. Do not tell it which provider to give the child.
   5. **Top-up, after CT-4 merges.** In the same project start a second Cursor thread on `composer-2.5`. Send one short message with Fast mode on (`Reply with one word: ready.`), then switch Fast mode off and send the same message again. That is check 3. In the same thread, with Fast mode off, send: `Start the implementer subagent and then the code-reviewer subagent. Ask each to reply with one line naming the model it runs on, and to change no files.` That backs check 1 if the CT-4 child started no subagent.
   6. Reply here with `CHIEF OF STAFF:`, the Cursor Chief of Staff thread id, the top-up thread id, the time of each Fast mode message, and how far CT-4 got. The child thread ids are read from the threads.
5. **Read the run.** With `t3_thread_read`, read the Cursor Chief of Staff thread, each child it started and the top-up thread. For each check below, record the result from a quoted tool call or reply, not a guess. List every thread and subagent the run starts for the Harness consistency table, and read the CW-275 Chief of Staff thread and this child for the Claude Code control line.
6. **Files and stores.** Read the trial root checkout's `.agent-team/state.json` and `.agent-team/gantt/`, run the dashboard API for the trial repo (`agent-team/scripts/dashboard/server.ts`, `/api`), and run `agent_usage.py --ticket CT-4` from the trial clone. Read the trial PR's comments with `gh.sh`. Open each `index.db` in the trial clone's stores under `~/.cursor/projects/` read-only (`sqlite3 'file:...?mode=ro'`) and list each run's agent, model and any field that names Fast mode. Write nothing in the trial repo or its stores.
7. **Tickets.** File one ticket in collective-wisdom per failure with the `write-ticket` skill, linking its cell, gap or check. Fix nothing.
8. **Docs.** Edit `docs/compatibility.md` and the skill paragraph (§ Doc changes), then open the PR.

### What the run checks

| Check | Works when |
|---|---|
| Child provider | The Chief of Staff's `delegate_task` for CT-4 passes `providerInstanceId: "cursor"` and model `grok-4.7`, and the child thread's provider reads `cursor` |
| Ship loop child threads | The Cursor child runs ship-loop to `MERGED #N`: spec pushed and `BUILD READY`, PR opened, a code review comment and a security review comment ending `Verdict: PASS` (a docs-only skip counts if the comment says so), a `## Docs check` comment, and `merge_pr.py` merges |
| G1, rule file | The thread quotes the rule file's first line and names `collective-wisdom.mdc` or Cursor rules as the source, before any skill file is read |
| G9, gantt | `.agent-team/gantt/` in the trial root checkout holds a snapshot for the Cursor Chief of Staff thread, and the dashboard API shows a gantt row for it |
| Harness consistency | Every thread and subagent the run starts runs on the Chief of Staff's own provider, `cursor` (see below) |
| Routing checks 1 to 4 | See § Routing checks |

### Routing checks

Each result is `works`, `partial`, `not supported` or `untested`, rests on something quoted from a store, a thread or a script's output, and has a ticket link where it is not `works`.

| Check | Works when | Read from |
|---|---|---|
| 1. Subagent `model:` | Each `.cursor/agents` subagent the CT-4 child or the top-up thread started records the model its file names (`composer-2.5` for the implementer, documenter and compacter, `grok-4.7` for the code reviewer), not the parent thread's model | The subagent's `index.db` rows and its transcript under `agent-transcripts/`, and its own one-line reply in the top-up |
| 2. `t3_thread_configure` mid-thread | The Chief of Staff's `t3_thread_configure` moves the CT-4 child to `composer-2.5` before the spec-approval relay, and the child's later runs record `composer-2.5` | The configure call in the Chief of Staff thread, and the child's runs in the store |
| 3. Fast mode | The store records Fast mode on a run, as a field or as a model id that differs from the standard one, so `agent_usage.py` could price it at its own rate | The store schema and rows of the top-up's two Fast mode runs, side by side |
| 4. `agent_usage.py --ticket` | `agent_usage.py --ticket CT-4`, run from the trial clone with the default `--cursor-projects`, prints a cost with a `Cursor $` part above zero and no `no price for` or `cannot read a Cursor store`, and the store holds runs on both `grok-4.7` and `composer-2.5` | The script's output and the per-model run counts from the store |

`partial` means part of a check holds: for example, the implementer honors `model:` but the code reviewer runs on its parent's model, or only one routed model is priced. A check with no evidence even after the top-up stays `untested` and gets a ticket. The security review is not in check 1: on Cursor it is a general subagent given `security-review.md` (CW-254), not a `.cursor/agents` file, and a docs-only CT-4 may skip it.

### Harness consistency

One Chief of Staff runs on one harness: a Cursor Chief of Staff starts only Cursor children, and a Claude Code one only Claude Code children, per the routing in `chief-of-staff/SKILL.md` § Models. The Runs entry gets a table with one row for every thread and subagent the CT-4 run starts:

- the Chief of Staff thread itself,
- the CT-4 child, once per model it runs on (spec, then build and merge),
- the project manager hygiene child and each Backlog ranking child, if it starts any,
- a ticket helper, if it starts one,
- each subagent a child starts (implementer, compacter, code reviewer, security reviewer or its general subagent, documenter).

Each row gives the thread id or subagent name, who started it, its provider and its model, and where that came from: the `delegate_task` or `t3_thread_configure` call, the thread's provider in `t3_thread_read`, or the model id in the Cursor run store. A row whose provider is not `cursor` is flagged. A row whose provider the threads and stores do not show is flagged `unknown`. The top-up thread is the user's, not the Chief of Staff's, so it is listed under the table and not checked.

The Ship loop child threads cell and G3 can be `works` only when no row is flagged. A flagged row makes the cell `partial`, names the row, and gets a ticket link on G3.

### Claude Code control line

The Runs entry gets one control line for the Claude Code column, from threads that already exist, so it costs no extra run: the collective-wisdom Chief of Staff thread that started this CW-275 child (Claude Code), this child, and the subagents this child starts during the build. Each gets the same provider and model fields, flagged if its provider is not `claudeAgent`. The line is read with `t3_thread_read` and costs nothing beyond that. If those threads do not show the provider and model for every row, the control line is dropped from the entry and a follow-up ticket covers a Claude Code control run.

Cells the run touches but the ticket does not ask about (Subagents G4, Security review G11, Stop hook) get a note in the entry when the run shows something, and keep their value unless the run settles them.

### Ship loop cell result

- `works` when every Ship loop check above holds and the Harness consistency table has no flagged row. G3 is then dropped, per `## Keeping it current`.
- Otherwise `partial` or `not supported`, saying what broke (and naming any flagged row), with a ticket link on G3.

## Doc changes

- **`docs/compatibility.md`, Runs:** a new entry above the CW-256 one, with the checks above, the Harness consistency table, the Claude Code control line and the routing evidence.
- **`docs/compatibility.md`, Matrix 1:** the Ship loop child threads cell, the Install cell (G1), the Local dashboard cell if the run settles it, and the Usage and cost report Cursor cell (checks 3 and 4).
- **`docs/compatibility.md`, Matrix 1 Notes:** one bullet, "Cursor model routing", with the four results, one line of evidence each, a ticket link where not `works`, and a link to the Runs entry.
- **`docs/compatibility.md`, Gaps:** G1, G3 and G9 per the run; in G8 the sentences about `grok-4.7`, `composer-2.5` and Fast mode are rewritten to the results of checks 3 and 4, with ticket links. The rest of G8 (Codex, Antigravity, `--context`) stays.
- **`docs/compatibility.md`, "Last checked" line:** set to the build date and the run.
- **`agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models `### Cursor`:** the "Not yet observed (CW-256)" paragraph becomes a short "Observed (CW-275 run)" paragraph with the results of checks 1 to 3, a ticket link for each failure, and a pointer to the compatibility note. The routing table stays as it is: changing it is a fix.

## Calls I made (surprising first)

- **The run includes a top-up thread after CT-4 merges**: two Fast mode messages (one on, one off) for check 3, plus asking the `implementer` and `code-reviewer` subagents to name their model, in case the CT-4 child started none. It sits in the one hand-off, so the build stops only once for you. One message runs at Fast mode rates.
- **A subagent's provider comes from the Cursor run store or the thread that started it.** T3 does not list subagents as threads, so where neither shows the provider the row is flagged `unknown`, which also keeps the cell from `works`.
- **The Claude Code control line reads this ticket's own threads** (the collective-wisdom Chief of Staff, this child, and its subagents) instead of starting a second run. It is dropped, with a follow-up ticket, if those threads do not show every provider and model.
- **The build waits on PR #277 and stops if it has not merged.** This ticket edits the Runs entry and cells that PR adds; starting from `main` without it would fork the doc.
- **The build stops halfway for you to start the Cursor thread**, as CW-256 did. That `BLOCKED:` is planned.
- **You start the Chief of Staff thread on `composer-2.5`, Fast mode off**, the model § Models Cursor names for it, so the run tests the routing as written.
- **G1 is tested with one question before `start the team`**: ask the thread to quote the rule. A thread that only finds the skills by searching would not know the rule's first line.
- **The child files trial ticket CT-4** in `dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker". Docs-only, so the security review may skip; the cell accepts a skip comment that ends `Verdict: PASS`.
- **The routing results go in a new Notes bullet and the skill paragraph, with evidence in the Runs entry.** The routing table in the skill does not change even if a check fails; the failure's ticket covers the fix.
- **The security review is left out of check 1**, since on Cursor it is a general subagent with a prompt, not a `.cursor/agents` file with `model:`.
- **The trial store and repo are read-only for the build.** Stores open with SQLite `mode=ro`, and `agent_usage.py` is read-only already.
- **The trial clone goes to `~/Documents/git/cw-cursor-trial`**, next to the other repos; the CW-256 clone at `~/Documents/cw-cursor-trial` is gone.
- **The child does not run `install.sh`.** The machine install is already current; if it is not, the run stops and asks you.
- **No new gap number.** Failures go on G1, G3, G8 and G9; a new gap only if the run finds something no gap covers.

## Leaves out

- Fixing anything that fails (one ticket each), including pricing Fast mode or Grok long prompts and any change to the routing table.
- Codex and Antigravity runs.
- Any change to scripts, `prices.json`, `install.sh` or the `.cursor/agents` files.
- The general one-harness-per-Chief-of-Staff rule in `chief-of-staff/SKILL.md` and a script check that flags a child on another provider. Both belong to a separate team-change ticket.
- A separate Claude Code control run. It happens only if the control line above is dropped, and then a follow-up ticket covers it.
- Closing #273 (the Chief of Staff does that).
- Deleting the trial repo or the clone.

## Touches

None of: data, money, auth, user email, migrations. It files one issue in the private trial repo, the run merges one PR there, and the top-up spends one message at Fast mode rates.

**Risk: Medium.** The spec edits a paragraph in `agent-team/.claude/skills/chief-of-staff/SKILL.md`, which is on the approval path and the hands path, so the spec and the merge wait for your approval. The edit is a prose note; the routing table and every instruction stay as they are.
