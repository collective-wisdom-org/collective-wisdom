# CW-275: Route Cursor to Auto, then run the Cursor trial with Cursor child threads (follow-up)

**Status:** Shipped
**Ticket:** [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275) (also covers [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273), closed as a duplicate)
**Shipped:** in PR #283, as specified

## Goal

This PR ships the Cursor routing change. The user's Cursor cannot pick models, so the routing moves from named models to Cursor's Auto router: Auto Intelligence is `auto-smart` with `optimize_for` `intelligence` (it replaces `grok-4.7`), and Auto Fast is `auto-smart` with `optimize_for` `balanced` (it replaces `composer-2.5`). Cursor's catalog has no fast option on Auto, so "Auto Fast" is the user's name for the balanced tier.

The Cursor trial run is a follow-up ticket, not part of this PR (see `## Follow-up ticket: the Cursor trial run`). The follow-up finds out whether a ship-loop child running on Cursor takes a ticket to `MERGED #N`, now that CW-272 routes a Cursor Chief of Staff's children to Cursor models, and whether the Auto routing holds up in a real run. It records the run in `docs/compatibility.md` § Runs, sets the Ship loop child threads cell on the Cursor column, says what the run showed for the rule file (G1) and the Cursor gantt hooks (G9), and gives each of the four routing checks from #273 a result:

1. Does a Cursor subagent run the model its file names, `auto-smart[optimize_for=intelligence]` for the code reviewer and `auto-smart[optimize_for=balanced]` for the implementer, documenter and compacter, read from the subagent's `runs.model` and `runs.model_params_json` (`optimize_for` value), not the parent's?
2. Does `t3_thread_configure` switch a Cursor child to `auto-smart` `balanced` partway through a thread?
3. What does the run store record for an Auto run (the model Auto routed to, and the `optimize_for` value in `model_params_json`), and does it still tell a `fast` true run from a false one on a model that has the option (the CW-256 run on `composer-2.5` recorded `[{"id":"fast","value":"true"}]`)?
4. What does `agent_usage.py --ticket` report for a real run on Auto?

Then it replaces the "Not yet observed" paragraph in `chief-of-staff/SKILL.md` § Models `### Cursor` with what was observed.

## Shipped in this PR

The user chose to ship the routing first and run the trial in a follow-up. Cursor sessions read the machine install and the root checkout stays on `main`, so the routing has to be merged and `./install.sh` re-run before a Cursor run can test it.

- **The routing table** in `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models `### Cursor`: Auto Intelligence and Auto Fast replace `grok-4.7` and `composer-2.5`.
- **Its mirrors:** `startup.md`, the configure row, `build-from-plan`, `open-pr`, `security-review`, `ship-loop`, the role docs, both `AGENTS.md` files, and the five `.cursor/agents/*.md` files.
- **The two tests** that read the routing: `test_agent_files.py` and `test_cursor_routing.py`.
- **`docs/compatibility.md`:** the Usage and cost report row's Cursor cell and G8, rewritten to say Auto runs show `cost unknown`.

Auto has no price, since it bills at the list price of the model each request is routed to, so the cost report shows `cost unknown` for Auto runs.

Not changed: the scripts, `prices.json`, `install.sh` and the `.claude/agents` files. The `grok-4.7` and `composer-2.5` price rows stay for anyone who picks those models.

## Today

Facts from `main` at `304891f` and the machine, read 2026-11-09.

- `docs/compatibility.md` on `main` now has `## Recording a run`, `## Runs`, the CW-256 run entry and the `partial` Ship loop cell, from PR #277 (CW-256), which merged; the follow-up edits that text.
- The machine install (`~/.collective-wisdom`) points at the root checkout, at `304891f`: it includes CW-272 (Cursor model routing) and CW-258 (Cursor gantt hooks). It has the CW-272 routing, not the Auto routing: `~/.cursor/agents/*.md` pin the new Auto values only once this change is on main and `install.sh` has run.
- `install.sh` has been run with those skills: `~/.cursor/rules/collective-wisdom.mdc` exists, `~/.cursor/hooks.json` holds the `cursor_gantt_hook.ts` entries and the `cos_rotation_check.py --hook` stop hook, and `~/.cursor/agents/*.md` pin `grok-4.7` (code-reviewer, security-reviewer) and `composer-2.5` (implementer, documenter, compacter) until then.
- `dbeallor/cw-cursor-trial` exists with issue #1 (CT-1, closed) and PRs #2 and #3 (merged). It already has `docs/agents/project.md` from the CW-256 run. No local clone of it is on the machine any more.
- `chief-of-staff/SKILL.md` § Models `### Cursor` on `main` (before this change): a Chief of Staff whose own provider is `cursor` starts the spec child on `grok-4.7` and switches it to `composer-2.5` for build and merge; helper children run on `composer-2.5`. This ticket changes the table to Auto Intelligence and Auto Fast. The section ends with a "Not yet observed" paragraph, listing what is still open.
- Facts read 2026-11-13: T3's Cursor catalog lists `auto-smart` (label "Auto") with one option `optimize_for` (values `intelligence`, `balanced`, `cost`; default `balanced`). Cursor's cursor-router doc says Balance and Intelligence bill at the list price of the model each request is routed to, so Auto runs have no per-id price. `fastMode` and `reasoning_effort` do not exist on Auto. A subagent file's `model:` takes an id with optional bracket parameters, but Cursor's subagent doc lists only concrete ids and `inherit`, so whether a subagent honors Auto is unproven.
- `docs/compatibility.md` on `main`: the Usage and cost report row's Cursor cell and G8 say Grok long prompts and Fast mode are priced at the standard rate. This ticket rewrites both to say Auto runs show `cost unknown`.
- The CW-256 run cannot answer the routing checks: it ran on skills from before CW-272, and no Cursor child or Cursor subagent ran.

## Follow-up ticket: the Cursor trial run

Not part of this PR. The follow-up ticket the Chief of Staff files carries it, and it starts only after this PR merges and `./install.sh` is re-run. The rest of this section is that ticket's spec.

### The run

A ship-loop child cannot start a Cursor thread (its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`), so the user starts it, as in CW-256. The build stops once for the user with `BLOCKED: Cursor run needed` and picks up when the Chief of Staff relays that the run and its top-up are done. The ticket changes markdown files only (the doc and one skill paragraph), so the build works from this spec and writes no plan.

#### Build steps

1. **Check #277 is merged** (it is as of 2026-11-13); if not, stop with `BLOCKED: waiting on #277`. This ticket edits the `## Runs` entry, the Ship loop cell, G1, G3 and G9 that PR #277 writes. Merge `origin/main` into this branch.
2. **Machine check.** Confirm the install is current: `git -C ~/.collective-wisdom rev-parse HEAD` is at or after `304891f`, and the rule file, hooks and agent files above are in place. Record the commit. If any is missing, stop with `BLOCKED:` and ask the user to run `./install.sh` from the root checkout; the child does not run it (it writes to `$HOME` and links the root checkout).
3. **Trial ticket.** File one new issue in `dbeallor/cw-cursor-trial` with `~/.collective-wisdom/scripts/gh.sh issue create -R dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker", type Improvement, one sentence of scope. It gets the next issue number, so its id is `CT-4`. Give it the labels the trial repo's tracker adapter needs to be ready for the team (the ones CT-1 had).
4. **Hand-off.** Stop with `BLOCKED: Cursor run needed` and these steps for the user:
   1. Clone `dbeallor/cw-cursor-trial` to `~/Documents/git/cw-cursor-trial` (or pull an existing clone to `main`) and add it as a T3 Code project if it is not one.
   2. In that project start a new thread with the Cursor provider and model Auto with Balanced ("Auto Fast", `auto-smart` with `optimize_for` `balanced`), the Chief of Staff model in § Models Cursor.
   3. Before `start the team`, send: `Quote the first line of your collective-wisdom rule, and say where it came from.` This is the G1 check.
   4. Send `start the team`. Approve the spec and the merge for CT-4 from that thread when it asks. Do not tell it which provider to give the child.
   5. **Top-up, after CT-4 merges.** In the same project start a second Cursor thread on Auto with Balanced. Send: `Start the implementer subagent and then the code-reviewer subagent. Ask each to reply with one line naming the model it runs on, and to change no files.` That backs check 1 if the CT-4 child started no subagent.
   6. Reply here with `CHIEF OF STAFF:`, the Cursor Chief of Staff thread id, the top-up thread id, and how far CT-4 got. The child thread ids are read from the threads.
5. **Read the run.** With `t3_thread_read`, read the Cursor Chief of Staff thread, each child it started and the top-up thread. For each check below, record the result from a quoted tool call or reply, not a guess. List every thread and subagent the run starts for the Harness consistency table, and read the CW-275 Chief of Staff thread and this child for the Claude Code control line.
6. **Files and stores.** Read the trial root checkout's `.agent-team/state.json` and `.agent-team/gantt/`, run the dashboard API for the trial repo (`agent-team/scripts/dashboard/server.ts`, `/api`), and run `agent_usage.py --ticket CT-4` from the trial clone. Read the trial PR's comments with `gh.sh`. Open each `index.db` in the trial clone's stores under `~/.cursor/projects/` read-only (`sqlite3 'file:...?mode=ro'`) and list each run's agent, model and any field that names Fast mode. Write nothing in the trial repo or its stores.
7. **Tickets.** File one ticket in collective-wisdom per failure with the `write-ticket` skill, linking its cell, gap or check. Fix nothing.
8. **Docs.** Edit `docs/compatibility.md` and the skill paragraph (§ Doc changes), then open the PR.

#### What the run checks

| Check | Works when |
|---|---|
| Child provider | The Chief of Staff's `delegate_task` for CT-4 passes `providerInstanceId: "cursor"` and model `auto-smart` with `optimize_for` `intelligence`, and the child thread's provider reads `cursor` |
| Ship loop child threads | The Cursor child runs ship-loop to `MERGED #N`: spec pushed and `BUILD READY`, PR opened, a code review comment and a security review comment ending `Verdict: PASS` (a docs-only skip counts if the comment says so), a `## Docs check` comment, and `merge_pr.py` merges |
| G1, rule file | The thread quotes the rule file's first line and names `collective-wisdom.mdc` or Cursor rules as the source, before any skill file is read |
| G9, gantt | `.agent-team/gantt/` in the trial root checkout holds a snapshot for the Cursor Chief of Staff thread, and the dashboard API shows a gantt row for it |
| Harness consistency | Every thread and subagent the run starts runs on the Chief of Staff's own provider, `cursor` (see below) |
| Routing checks 1 to 4 | See § Routing checks |

#### Routing checks

Each result is `works`, `partial`, `not supported` or `untested`, rests on something quoted from a store, a thread or a script's output, and has a ticket link where it is not `works`.

| Check | Works when | Read from |
|---|---|---|
| 1. Subagent `model:` | Each `.cursor/agents` subagent the CT-4 child or the top-up thread started runs the model its file names: `runs.model` is `auto-smart` and `runs.model_params_json` holds `optimize_for` `balanced` for the implementer, documenter and compacter and `intelligence` for the code reviewer, not the parent thread's values | The subagent's `index.db` rows and its transcript under `agent-transcripts/`, and its own one-line reply in the top-up |
| 2. `t3_thread_configure` mid-thread | The Chief of Staff's `t3_thread_configure` moves the CT-4 child to `auto-smart` `balanced` before the spec-approval relay, and the child's later runs record `optimize_for` `balanced` | The configure call in the Chief of Staff thread, and the child's runs in the store |
| 3. Auto in the run store | The store records what Auto routed to and the `optimize_for` value in `model_params_json` for an Auto run, and still tells a `fast` true run from a false one on a model that has the option (the CW-256 run on `composer-2.5` recorded `[{"id":"fast","value":"true"}]`) | The store schema and rows of the CT-4 runs, and the CW-256 run's recorded rows |
| 4. `agent_usage.py --ticket` | `agent_usage.py --ticket CT-4`, run from the trial clone with the default `--cursor-projects`, prints `cost unknown (no price for auto-smart...)` or the name of whatever the store records, never a cost line that hides the Auto runs | The script's output and the per-model run counts from the store |

`partial` means part of a check holds: for example, the implementer honors `model:` but the code reviewer runs on its parent's model. Check 4 is `partial` if the script prices the Auto runs as a number. A check with no evidence even after the top-up stays `untested` and gets a ticket. The security review is not in check 1: on Cursor it is a general subagent given `security-review.md` (CW-254), not a `.cursor/agents` file, and a docs-only CT-4 may skip it.

#### Harness consistency

One Chief of Staff runs on one harness: a Cursor Chief of Staff starts only Cursor children, and a Claude Code one only Claude Code children, per the routing in `chief-of-staff/SKILL.md` § Models. The Runs entry gets a table with one row for every thread and subagent the CT-4 run starts:

- the Chief of Staff thread itself,
- the CT-4 child, once per model it runs on (spec, then build and merge),
- the project manager hygiene child and each Backlog ranking child, if it starts any,
- a ticket helper, if it starts one,
- each subagent a child starts (implementer, compacter, code reviewer, security reviewer or its general subagent, documenter).

Each row gives the thread id or subagent name, who started it, its provider and its model, and where that came from: the `delegate_task` or `t3_thread_configure` call, the thread's provider in `t3_thread_read`, or the model id in the Cursor run store. A row whose provider is not `cursor` is flagged. A row whose provider the threads and stores do not show is flagged `unknown`. The top-up thread is the user's, not the Chief of Staff's, so it is listed under the table and not checked.

The Ship loop child threads cell and G3 can be `works` only when no row is flagged. A flagged row makes the cell `partial`, names the row, and gets a ticket link on G3.

#### Claude Code control line

The Runs entry gets one control line for the Claude Code column, from threads that already exist, so it costs no extra run: the collective-wisdom Chief of Staff thread that started this CW-275 child (Claude Code), this child, and the subagents this child starts during the build. Each gets the same provider and model fields, flagged if its provider is not `claudeAgent`. The line is read with `t3_thread_read` and costs nothing beyond that. If those threads do not show the provider and model for every row, the control line is dropped from the entry and a follow-up ticket covers a Claude Code control run.

Cells the run touches but the ticket does not ask about (Subagents G4, Security review G11, Stop hook) get a note in the entry when the run shows something, and keep their value unless the run settles them.

#### Ship loop cell result

- `works` when every Ship loop check above holds and the Harness consistency table has no flagged row. G3 is then dropped, per `## Keeping it current`.
- Otherwise `partial` or `not supported`, saying what broke (and naming any flagged row), with a ticket link on G3.

#### Doc changes (follow-up)

The Auto routing table and the Usage and cost report Cursor cell and G8 rewrite are this PR's changes (see `## Shipped in this PR`). The follow-up makes these:

- **`docs/compatibility.md`, Runs:** a new entry above the CW-256 one, with the checks above, the Harness consistency table, the Claude Code control line and the routing evidence.
- **`docs/compatibility.md`, Matrix 1:** the Ship loop child threads cell, the Install cell (G1), the Local dashboard cell if the run settles it, and the Usage and cost report Cursor cell as this PR rewrote it (checks 3 and 4).
- **`docs/compatibility.md`, Matrix 1 Notes:** one bullet, "Cursor model routing", with the four results, one line of evidence each, a ticket link where not `works`, and a link to the Runs entry.
- **`docs/compatibility.md`, Gaps:** G1, G3 and G9 per the run; in G8 the Cursor sentences are already rewritten by this PR for Auto (cost unknown), and are adjusted to the results of checks 3 and 4, with ticket links. The rest of G8 (Codex, Antigravity, `--context`) stays.
- **`docs/compatibility.md`, "Last checked" line:** set to the build date and the run.
- **`agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models `### Cursor`:** the "Not yet observed (CW-256)" paragraph becomes a short "Observed (CW-275 run)" paragraph with the results of checks 1 to 3, a ticket link for each failure, and a pointer to the compatibility note. The routing table is the Auto routing this PR ships; a later change to it is a fix.

## Calls I made (surprising first)

- **The routing change is part of this ticket's scope**, because your Cursor cannot pick models. Auto Intelligence is `auto-smart` with `optimize_for` `intelligence` and Auto Fast is `auto-smart` with `optimize_for` `balanced`; that naming is your choice. It replaces `grok-4.7` and `composer-2.5` in the routing table, the `.cursor/agents` files, the skills and role docs that mention them, and the two tests that read them.
- **Auto has no price in `prices.json`**, since it bills at the list price of the model each request is routed to, so the cost report shows `cost unknown` for Auto runs. Scripts and `prices.json` do not change; the `grok-4.7` and `composer-2.5` rows stay for anyone who picks them.
- **Settled: the routing PR ships first, and the run is a follow-up ticket the build does not file.** The Cursor run only tests the new routing once it is merged to `main` and `install.sh` is re-run, because Cursor sessions read the machine install and the root checkout stays on `main`. So the routing change and the run record cannot be one PR without the run testing the old routing. The user chose this option, via the Chief of Staff. The Chief of Staff files the follow-up ticket.
- **Follow-up: the run includes a top-up thread after CT-4 merges**: one message asking the `implementer` and `code-reviewer` subagents to name their model, in case the CT-4 child started none. It sits in the one hand-off, so the build stops only once for you.
- **Follow-up: a subagent's provider comes from the Cursor run store or the thread that started it.** T3 does not list subagents as threads, so where neither shows the provider the row is flagged `unknown`, which also keeps the cell from `works`.
- **Follow-up: the Claude Code control line reads this ticket's own threads** (the collective-wisdom Chief of Staff, this child, and its subagents) instead of starting a second run. It is dropped, with a follow-up ticket, if those threads do not show every provider and model.
- **Follow-up: the build checks PR #277 is merged, which it is.** The follow-up edits the Runs entry and cells that PR adds; it stops with `BLOCKED: waiting on #277` if that ever proves false, since starting from `main` without it would fork the doc.
- **Follow-up: the build stops halfway for you to start the Cursor thread**, as CW-256 did. That `BLOCKED:` is planned.
- **Follow-up: you start the Chief of Staff thread on Auto with Balanced ("Auto Fast")**, the model § Models Cursor names for it, so the run tests the routing as written.
- **Follow-up: G1 is tested with one question before `start the team`**: ask the thread to quote the rule. A thread that only finds the skills by searching would not know the rule's first line.
- **Follow-up: the child files trial ticket CT-4** in `dbeallor/cw-cursor-trial`: "Add a Contributing line to README.md that points to the issue tracker". Docs-only, so the security review may skip; the cell accepts a skip comment that ends `Verdict: PASS`.
- **Follow-up: the routing results go in a new Notes bullet and the skill paragraph, with evidence in the Runs entry.** The routing table in the skill does not change after this PR's Auto edit even if a check fails; the failure's ticket covers the fix.
- **Follow-up: the security review is left out of check 1**, since on Cursor it is a general subagent with a prompt, not a `.cursor/agents` file with `model:`.
- **Follow-up: the trial store and repo are read-only for the build.** Stores open with SQLite `mode=ro`, and `agent_usage.py` is read-only already.
- **Follow-up: the trial clone goes to `~/Documents/git/cw-cursor-trial`**, next to the other repos; the CW-256 clone at `~/Documents/cw-cursor-trial` is gone.
- **Follow-up: the child does not run `install.sh`.** The machine install is already current; if it is not, the run stops and asks you.
- **Follow-up: no new gap number.** Failures go on G1, G3, G8 and G9; a new gap only if the run finds something no gap covers.

## Leaves out

- Running the Cursor trial and filing the follow-up ticket for it. This PR does neither; the Chief of Staff files the follow-up.
- Fixing anything that fails (one ticket each), including pricing Fast mode or Grok long prompts and any further change to the routing table.
- A price for Auto in `prices.json` or `agent_usage.py`.
- Codex and Antigravity runs.
- Any change to scripts, `prices.json` or `install.sh`, apart from the two routing tests (`test_agent_files.py`, `test_cursor_routing.py`) that read the routing.
- The general one-harness-per-Chief-of-Staff rule in `chief-of-staff/SKILL.md` and a script check that flags a child on another provider. Both belong to a separate team-change ticket.
- A separate Claude Code control run. It happens only if the control line above is dropped, and then a follow-up ticket covers it.
- Closing #273 (the Chief of Staff does that).
- Deleting the trial repo or the clone.

## Touches

None of: data, money, auth, user email, migrations. This PR touches no repo outside collective-wisdom. The follow-up run files one issue in the private trial repo, merges one PR there, and spends one top-up message.

**Risk: Medium.** The ticket edits the routing table in `agent-team/.claude/skills/chief-of-staff/SKILL.md`, which is on the approval path and the hands path, so the spec and the merge wait for your approval. The edit is now a routing table edit, a behavior change on the approval path: every Cursor child, helper and subagent runs on Auto instead of a named model. Cost reports show `cost unknown` for those runs.
