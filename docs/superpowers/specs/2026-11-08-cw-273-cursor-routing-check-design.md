# CW-273: Check the Cursor model routing against a real Cursor run

**Status:** Draft
**Ticket:** [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273)
**Related:** [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275) (the run), [#272](https://github.com/collective-wisdom-org/collective-wisdom/issues/272) (the routing), [#256](https://github.com/collective-wisdom-org/collective-wisdom/issues/256) and PR [#277](https://github.com/collective-wisdom-org/collective-wisdom/pull/277) (the first Cursor run)

## Goal

CW-272 routes Cursor work to `grok-4.7` and `composer-2.5`. Nobody has seen that routing work in a Cursor run. This ticket gives each of four checks a result from a real run, writes the results down, and files a ticket for each one that is not `works`:

1. Does a Cursor subagent run on the model named by `model:` in `agent-team/.cursor/agents/<name>.md`?
2. Does `t3_thread_configure` switch a Cursor child to a new model partway through a thread?
3. Does the Cursor run store tell a Fast mode run apart from a standard one, so the cost report does not show too little?
4. Does `agent_usage.py --ticket` price a real run on each routed model?

## Today

Read 2026-11-09, `main` at `304891f`.

- The CW-256 run (PR #277, open) cannot answer these checks. It ran on skills at `070a3ca`, before CW-272: the Cursor Chief of Staff started every child on Claude Code, and no Cursor child or Cursor subagent ran. PR #277 says so in its Runs entry.
- [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275) is the next Cursor run, on skills that include CW-272. Its spec (`docs/superpowers/specs/2026-11-09-cw-275-cursor-trial-child-threads-design.md` on `feat/cw-275-cursor-trial-child-threads`, commit `0f822ba`, Draft) runs trial ticket CT-4 in `dbeallor/cw-cursor-trial` with a Cursor Chief of Staff on `composer-2.5`, Fast mode off, and says the run "also records the evidence #273 asks for" so #273 "needs no second run".
- `chief-of-staff/SKILL.md` § Models `### Cursor` ends with a "Not yet observed (CW-256)" paragraph listing checks 1 to 3 as open.
- `docs/compatibility.md` on `main`: the Usage and cost report row's Cursor cell says Grok long prompts and Fast mode are priced at the standard rate (G8), and G8 says the same.

## One run, two tickets

There is one Cursor run: #275's. This ticket starts no run of its own and never drives one. A ship-loop child cannot start a Cursor thread anyway (its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`).

| Who | Records |
|---|---|
| #275 | The run itself: the Runs entry in `docs/compatibility.md` (date, threads, how far CT-4 got), the raw evidence for this ticket (the model ids in each child's and subagent's run store, the Fast mode setting where the store shows it, and the `agent_usage.py --ticket CT-4` output), and its own cells: Child provider, Ship loop child threads, Mid-thread switch, G1, G3, G9, Install and Local dashboard. Tickets for its own failures. |
| #273 (this ticket) | The verdict on each of the four checks, read from #275's Runs entry and checked against the trial store. Its own doc lines: a routing Notes bullet, the Usage and cost report Cursor cell, G8, the "Last checked" line if it merges after #275, and the `### Cursor` paragraph in the skill. Tickets for checks 1, 3 and 4 when they are not `works`. |

Check 2 is #275's Mid-thread switch check under another name, and the same run answers it. #275 owns that result and its ticket. This ticket copies the result into its Notes bullet and the skill paragraph, linking #275's ticket if there is one, and files no second ticket for it.

### What the run does not cover

#275's run keeps Fast mode off throughout, as § Models says. So it has no Fast mode run next to a standard one, and check 3 cannot be answered from it. Check 3 needs a small top-up in the same trial repo: one Cursor thread on `composer-2.5`, one short message with Fast mode on and one with it off. That is two messages, not a second run. If #275's hand-off already included it, there is nothing to ask for.

## Evidence for each check

Each result is `works`, `partial` or `not supported` (the compatibility doc's words). A result rests on something read from the store, a thread or a script's output, and that thing is quoted in the doc. A check with no evidence after the top-up stays `untested` and gets a ticket.

| Check | Works when | Read from |
|---|---|---|
| 1. Subagent `model:` | Each subagent the Cursor child started in the CT-4 run records the model its `.cursor/agents/<name>.md` names (`composer-2.5` for the implementer, documenter and compacter, `grok-4.7` for the code reviewer), not the child thread's model | #275's Runs entry, checked against the subagent's `sdk-agent-store/*/index.db` rows (opened read-only) and its transcript under `agent-transcripts/`, in the trial clone's stores under `~/.cursor/projects/` |
| 2. `t3_thread_configure` mid-thread | #275's Mid-thread switch check is `works` | #275's Runs entry |
| 3. Fast mode | The store records Fast mode on a run, as a field or as a model id that differs from the standard one, so `agent_usage.py` could price it on its own rate | The store schema and rows of the top-up's two runs, side by side |
| 4. `agent_usage.py --ticket` | `agent_usage.py --ticket CT-4`, run from the trial clone with the default `--cursor-projects`, prints a cost with a `Cursor $` part above zero and no `no price for` or `cannot read a Cursor store`, and the store holds runs on both `grok-4.7` and `composer-2.5` | #275's recorded output, run again read-only at build time, and the per-model run counts from the store |

`partial` means part of the check holds. For example, the implementer honors `model:` but the code reviewer runs on the child's model, or only one routed model is priced. `not supported` means it does not hold at all. The security review is not in check 1: on Cursor it is a general subagent given `security-review.md` (CW-254), not a `.cursor/agents` file, and a docs-only CT-4 may skip it.

## Build steps

The ticket changes markdown files only, so the build works from this spec and writes no plan.

1. **Wait for #275.** Build reads the run from #275's merged Runs entry. If #275's PR has not merged when the build starts, stop with `BLOCKED: waiting on #275` and say what stage it is in. Once it has, merge `origin/main` into this branch.
2. **Read the run.** From the Runs entry take the thread ids and the evidence #275 recorded. Read the Cursor child thread with `t3_thread_read` where the entry leaves a check unclear. Open each `index.db` in the trial stores read-only (`sqlite3 'file:...?mode=ro'`) and list each run's agent, model and any field that names Fast mode. Run `agent_usage.py --ticket CT-4` from the trial clone. Write nothing in the trial repo or its stores.
3. **Top-up, only if needed.** If check 3 has no Fast mode run, or check 1 has no subagent run (for example the child started none), stop once with `BLOCKED: Cursor top-up needed` and only the steps for the missing checks, for the Chief of Staff or the user to do in a Cursor thread in the trial clone:
   - Check 1: ask it to start the `implementer` subagent and then the `code-reviewer` subagent, each on a one-line task.
   - Check 3: on `composer-2.5`, send one short message with Fast mode on and one with it off.
   - Reply here with `CHIEF OF STAFF:` and the thread id.

   Then read those runs as in step 2. Checks 2 and 4 get no top-up: check 2 takes #275's result, and if the CT-4 run has no `grok-4.7` or no `composer-2.5` run, check 4 says which model is missing and adds the top-up runs to its evidence when there are any.
4. **Tickets.** For each of checks 1, 3 and 4 that is not `works`, file one ticket in collective-wisdom with the `write-ticket` skill. It names the check, quotes the evidence and links back to the doc line. Fix nothing.
5. **Docs.** Write the results (next section), then open the PR.

## Doc changes

#275 and PR #277 edit `docs/compatibility.md` too. This ticket leaves their lines alone: the Runs entries, `## Recording a run`, the Install, Team skills load, Subagents, Chief of Staff thread, Ship loop child threads and Local dashboard cells, and G1, G3, G4 and G9. It edits only:

- **`docs/compatibility.md`, Matrix 1 Notes:** one new bullet, "Cursor model routing (CW-273)", with the four results. Each has one line of evidence, a ticket link where it is not `works`, and a link to #275's Runs entry for the run.
- **`docs/compatibility.md`, Usage and cost report row, Cursor cell:** updated to what checks 3 and 4 showed.
- **`docs/compatibility.md`, G8:** the sentences about `grok-4.7`, `composer-2.5` and Fast mode are rewritten to the results, with ticket links. The rest of G8 (Codex, Antigravity, `--context`) stays.
- **`docs/compatibility.md`, "Last checked" line:** set to the build date. #275 merges first (step 1), so this is a plain edit on top of its line.
- **`agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models, `### Cursor`:** the "Not yet observed (CW-256)" paragraph becomes a short "Observed (CW-275 run)" paragraph with the result of checks 1 to 3, a ticket link for each failure, and a pointer to the compatibility note. The routing table stays as it is: changing it is a fix, and fixes are out of scope.

Since this ticket builds on `main` after #275 merges, the two PRs cannot conflict.

## Calls I made (surprising first)

- **Check 3 needs a two-message Fast mode top-up that #275's run does not include.** #275 keeps Fast mode off, so its store has nothing to compare. The build asks for it once with `BLOCKED: Cursor top-up needed`. Adding the two messages to #275's hand-off would spare that stop; that is #275's call, not made here.
- **The build waits for #275 to merge, not just for its run to end.** It reads the evidence from the merged Runs entry and edits a doc that has it, so the two PRs never conflict. The cost is that this ticket finishes after #275.
- **#275 owns check 2 (its Mid-thread switch check) and any ticket for it.** This ticket copies the result and files no second ticket.
- **#275 records the raw evidence; this ticket gives the verdicts.** It still opens the stores and reruns `agent_usage.py` read-only, so a verdict never rests on a summary alone.
- **The security review is left out of check 1**, since on Cursor it is a general subagent with a prompt, not a `.cursor/agents` file with `model:`.
- **The results go in a new Notes bullet, not in #275's Runs entry.** That keeps each ticket on its own lines.
- **A check with no evidence stays `untested` and gets a ticket.** Calling it `works`, `partial` or `not supported` without evidence would be a guess.
- **The routing table in the skill does not change, even if a check fails.** The failure's ticket covers the fix.
- **The trial store and repo are read-only for this ticket.** Stores open with SQLite `mode=ro`, and `agent_usage.py` is read-only already.

## Leaves out

- Running or driving the Cursor run (#275).
- The Runs entry and the cells and gaps #275 and #277 own.
- Fixing any failure, including pricing Fast mode or Grok long prompts (each failure gets its own ticket).
- Codex and Antigravity runs.
- Any change to scripts, `prices.json`, `install.sh` or the `.cursor/agents` files.

## Touches

None of: data, money, auth, user email, migrations. A top-up, if needed, is a few short Cursor messages, one of them at Fast mode rates.
