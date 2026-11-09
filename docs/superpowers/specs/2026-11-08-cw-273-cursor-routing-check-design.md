# CW-273: Check the Cursor model routing against a real Cursor run

**Status:** Draft
**Ticket:** [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273)
**Related:** [#256](https://github.com/collective-wisdom-org/collective-wisdom/issues/256) (the Cursor run), [#272](https://github.com/collective-wisdom-org/collective-wisdom/issues/272) (the routing)

## Goal

CW-272 routes Cursor work to `grok-4.7` and `composer-2.5`. Nobody has seen that routing work in a Cursor run. This ticket checks four things against a real run, writes down the results, and files a ticket for each one that fails:

1. Does a Cursor subagent run on the model named by `model:` in `agent-team/.cursor/agents/<name>.md`?
2. Does `t3_thread_configure` switch a Cursor child to a new model partway through a thread?
3. Does the Cursor run store tell a Fast mode run apart from a standard one, so the cost report does not show too little?
4. Does `agent_usage.py --ticket` price a real run on each routed model?

## Which run

The ticket allows the CW-256 run or a new small one. This uses the CW-256 run. It is already under way: a Cursor store for `~/Documents/cw-cursor-trial` exists in `~/.cursor/projects/Users-david-beallor-Documents-cw-cursor-trial/`. Reusing it means no second trial repo and no second Chief of Staff.

A ship-loop child cannot start a Cursor thread: its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`. The Cursor CLI on this machine is also not logged in (`cursor-agent status` prints `Not logged in`). So this child only reads the run. It never drives it.

The CW-256 run may not cover every check. A Cursor child that never starts a subagent says nothing about check 1, and a run with no mid-thread switch says nothing about check 2. For each check the run does not cover, the build asks for a short top-up run once (see Build steps). It does not guess.

## Evidence for each check

Each result is `works`, `partial` or `not supported` (the compatibility doc's words). A result rests on something read from the store, a thread or a script's output, and that thing is quoted in the doc. A check with no evidence after the top-up stays `untested` and gets a ticket.

| Check | Works when | Read from |
|---|---|---|
| 1. Subagent `model:` | The subagent's run in the Cursor store records the model its `.cursor/agents/<name>.md` names (for example `composer-2.5` for the implementer, `grok-4.7` for the code reviewer), not the parent thread's model | The `sdk-agent-store/*/index.db` rows for the subagent's agent, opened read-only, and its transcript under `agent-transcripts/` |
| 2. `t3_thread_configure` mid-thread | After the Chief of Staff switches a Cursor child from `grok-4.7` to `composer-2.5` before the spec-approval relay, the child's next turn runs on `composer-2.5` in the store, and `t3_thread_read` shows the new model selection | The child's store rows before and after the switch, and the Chief of Staff thread's `t3_thread_configure` call and result |
| 3. Fast mode | The store records Fast mode on a run, as a field or as a model id that differs from the standard one, so `agent_usage.py` could price it on its own rate | The store schema and rows. Needs one Fast mode run next to a standard run on the same model to compare |
| 4. `agent_usage.py --ticket` | `agent_usage.py --ticket CT-1`, run from `~/Documents/cw-cursor-trial` with the default `--cursor-projects`, prints a cost with a `Cursor $` part above zero and no `no price for` or `cannot read a Cursor store`, and the store holds runs on both `grok-4.7` and `composer-2.5` | The script's output, and the per-model run counts from the store |

`partial` means part of the check holds. For example, the implementer honors `model:` but a reviewer runs on the parent's model, or Fast mode shows on one model and not the other. `not supported` means it does not hold at all.

## Build steps

The ticket changes markdown files only, so the build works from this spec and writes no plan.

1. **Wait for the run.** Build starts once the CW-256 run has got past its build stage (its child has started review subagents) or has ended. If CW-256's child is still in spec when this build starts, stop with `BLOCKED: waiting for the CW-256 Cursor run` and say what stage it is in.
2. **Read the run.** Read the Cursor Chief of Staff thread and each child thread with `t3_thread_read`, using the thread ids from CW-256's relay or its `## Runs` entry. Open each `index.db` in the trial store read-only (`sqlite3 'file:...?mode=ro'`) and list each run's agent, model and any field that names Fast mode. Run `agent_usage.py --ticket CT-1` from the trial clone. Write nothing in the trial repo or its store.
3. **Top-up run, only if needed.** If any of checks 1 to 3 has no evidence, stop once with `BLOCKED: Cursor top-up run needed` and only the steps for the missing checks, for the Chief of Staff or the user to do in the trial repo:
   - Check 1: in a Cursor thread in `~/Documents/cw-cursor-trial`, ask it to start the `implementer` subagent and then the `code-reviewer` subagent, each on a one-line task.
   - Check 2: start a Cursor thread on `grok-4.7`, send one message, switch it to `composer-2.5` with `t3_thread_configure` (`modelSelection: {instanceId: "cursor", model: "composer-2.5", options: {fastMode: false}}`), and send one more.
   - Check 3: in a Cursor thread on `composer-2.5`, send one short message with Fast mode on and one with it off.
   - Reply here with `CHIEF OF STAFF:` and the thread ids.

   Then read those runs as in step 2. Check 4 needs no top-up: if the CW-256 run has no `grok-4.7` or no `composer-2.5` run, the result says which model is missing and rests on the top-up runs, read with the same script.
4. **Tickets.** For each check that is not `works`, file one ticket in collective-wisdom with the `write-ticket` skill. It names the check, quotes the evidence and links back to the doc line. Fix nothing.
5. **Docs.** Write the results (next section), then open the PR.

## Doc changes, and how they fit with CW-256

CW-256 is building in another worktree and also edits `docs/compatibility.md`. Its spec owns these parts of that file: the Cursor cells for Team skills load, Chief of Staff thread, Ship loop child threads and Local dashboard, the G3 line, and the new `## Recording a run` and `## Runs` sections. This ticket does not touch them. It also leaves the Subagents cell and G4 alone, which CW-256 leaves to #255.

This ticket edits only:

- **`docs/compatibility.md`, Matrix 1 Notes:** one new bullet, "Cursor model routing (CW-273)", with the four results. Each result has one line of evidence and a ticket link where it is not `works`. It names the run by date and thread ids, and links CW-256's `## Runs` entry if CW-256 has merged by then.
- **`docs/compatibility.md`, Usage and cost report row, Cursor cell:** updated to what checks 3 and 4 showed. Today it says Grok long prompts and Fast mode are priced at the standard rate.
- **`docs/compatibility.md`, G8:** the sentences about `grok-4.7`, `composer-2.5` and Fast mode are rewritten to the results, with ticket links. The rest of G8 (Codex, Antigravity, `--context`) stays as it is.
- **`docs/compatibility.md`, "Last checked" date:** set to the build date. CW-256 may change the same line. Whichever ticket merges second keeps the later date when it resolves the conflict.
- **`agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models, `### Cursor`:** the "Not yet observed (CW-256)" paragraph becomes a short "Observed (CW-273)" paragraph. It gives the result of checks 1 to 3, a ticket link for each failure, and a pointer to the compatibility note. The routing table stays as it is: changing it is a fix, and fixes are out of scope.

None of these lines are in CW-256's diff, so the two PRs merge in either order. Whichever is second rebases, and only the "Last checked" line can conflict.

## Calls I made

- **This build stops for a top-up Cursor run if the CW-256 run leaves a check unanswered.** A child can't start a Cursor thread, and the CLI here is not logged in. So a run the user or the Chief of Staff starts is the only way to get evidence. The stop is planned. It is not a failure.
- **The top-up run uses the CW-256 trial repo** (`~/Documents/cw-cursor-trial`), not collective-wisdom or a new repo. A Cursor thread here would share a root checkout with the running Chief of Staff.
- **Check 3 needs one short Fast mode run.** The store can't show how it marks Fast mode without a run that used it. Two one-line messages cost very little at Fast rates.
- **The build waits for CW-256's run to reach review**, so that run's subagents and its switch to `composer-2.5` before the build stage can count as evidence and spare a top-up.
- **The results go in a new Notes bullet, not in CW-256's `## Runs` entry or the Subagents cell.** That keeps the two PRs off each other's lines.
- **A check with no evidence stays `untested` and gets a ticket.** The ticket asks for works, partial or not supported. Calling a check one of those without evidence would be a guess.
- **The routing table in the skill is not changed, even if a check fails.** The failure's ticket covers the fix.
- **The trial store and repo are read-only for this ticket.** Stores open with SQLite `mode=ro`, and `agent_usage.py` is read-only already.

## Leaves out

- Fixing any failure, including pricing Fast mode or Grok long prompts (each failure gets its own ticket).
- Codex and Antigravity runs.
- The Subagents cell and G4 (#255), and the cells, G3 and sections CW-256 owns.
- Any change to scripts, `prices.json`, `install.sh` or the `.cursor/agents` files.

## Touches

None of: data, money, auth, user email, migrations. A top-up run, if needed, is a few short Cursor messages, one of them at Fast mode rates.
