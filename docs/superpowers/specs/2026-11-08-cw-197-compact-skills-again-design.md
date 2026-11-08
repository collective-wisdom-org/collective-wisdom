# CW-197: Compact the skills and role docs again, and move more logic into scripts

**Ticket:** [CW-197](https://github.com/collective-wisdom-org/collective-wisdom/issues/197)
**Status:** Shipped
**Shipped:** in PR #207, with differences: [as-built](../as-built/2026-11-08-cw-197-compact-skills-again-as-built.md)

## Goal

Shrink the agent text that grew back since CW-23 and CW-115, without losing a rule, gate or command. Three ways: say each rule once and point to its owner, cut prose that restates a script's docstring, and give the model a script where it follows fixed steps to a fixed answer. Scripts read and print; T3 calls and tracker writes stay with the model.

## Today

Re-measured on `main` at `c7d8df0` (after CW-60 merged), 2026-11-08, in characters (Python `len` of the decoded text, the unit `compact_check.py` uses; `wc -c` gives bytes and reads a few dozen higher).

| File | Characters |
|---|---|
| `chief-of-staff/SKILL.md` | 84364 |
| `chief-of-staff/` siblings (10 files) | 82386 |
| `ship-loop/SKILL.md` | 23238 |
| `open-pr/SKILL.md` | 19410 |
| `project-manager/SKILL.md` | 15525 |
| `chief-of-staff/rotation.md` | 15548 |
| `docs/agents/trackers/github.md` | 13138 |
| `chief-of-staff/approvals.md` | 12951 |
| `docs/agents/org-chart.md` | 12927 |
| `merge-pr/SKILL.md` | 9035 |
| `docs/agents/chief-of-staff.md` | 8172 |
| Every file `compact_check.py` counts (45 files) | 348854 |

`chief-of-staff/SKILL.md` by section (approximate): Tick 11200, Commands 9900, Send or queue 8300, Sweep 8100, Child path 7700, Report format 6800, the intro 4100, State file 3800, Tools 3400, Guardrails 3000, Lean turns 2900, Models 2500, everything else under 2000 each.

### Overlap with CW-199

CW-199 (run the docs check once, after both reviews pass; spec on `feat/cw-199-docs-check-once`, in build now) edits:

- `open-pr`: § Docs check, § Closeout docs (the rerun sentence), § Agent review comment loop, § Done when, § Conflict resolution step 4, § CI review mode.
- `ship-loop`: § Phase gates, § Phases 3 and 4.
- `docs/agents/code-review.md` § Method, the stage diagram and Documenter row of `docs/agents/org-chart.md`, and the `documenter.md` and `code-reviewer.md` agent descriptions.
- `review_gate.py` and `merge_pr.py`.

This ticket leaves all of those alone. It cuts only the other sections of `open-pr` and `ship-loop`, and the rest of `org-chart.md`. The two PRs then touch neighbouring lines at most, and whichever merges second rebases. If CW-199 merges first, the build rebases onto it before cutting and re-measures the two skills; the size targets for `open-pr` and `ship-loop` below are deltas, so they still apply.

## Design

### 1. Send or queue routing: new `cos_route.py`

Today `chief-of-staff/SKILL.md` § Send or queue states the lane rule (room in the lane, room under the cap, nobody already queued in that lane) and an 11-row caller table that maps a caller and the ticket's stage to a lane. The model works out the lane, the counts, the queue check and the continuation check by hand on every relay.

New `agent-team/scripts/cos_route.py <PREFIX>-N <caller>`. Callers: `approve-spec`, `approve-merge`, `changes`, `reviewer-changes`, `head-moved`, `conflict-keep`, `conflict-withdraw`, `answer`, `resume`, `rate-limit`. It reads `.agent-team/state.json` through `cos_state.load`, the lane limits from `cos_tick.LIMITS` and `cos_tick.CAP` (imported, not copied, and `cos_tick.py` is not edited), and `Review after conflict resolution` from `project_config` for the conflict rows. It prints one last line:

| Line | Meaning |
|---|---|
| `route: send <lane>` | Send now with `t3_thread_send`, then the printed `stage` op. |
| `route: queue <lane>` | Don't send; apply the printed `stage` op to `<lane>-queued` (the model adds `pendingRelay` and, for a user spec approval, `approvalItemId`). |
| `route: continuation <lane>` | `parentThreadId` is known and is not `chiefThreadId`: continuation.md § Continuation child, in place of the send. |
| `route: no <why>` exit 1 | The caller doesn't apply from the ticket's stage (for example `approve-merge` from `awaiting-build`). Don't send. |
| exit 2, `route: cannot <what>` | State unreadable or a bad argument. |

`send` lines from a ticket whose `parentThreadId` is not this thread also print the `I may not hear when this run ends` Moving line, so the model copies it rather than recalls when it applies. The § Models switch stays a model step, named once in the caller's row.

§ Send or queue keeps the relay texts, the verification steps (user check, `cos_approve_pr.py`, `cos_head_check.py`), the auto-approval notice and the continuation pointer, and replaces the lane rule and the caller table with "run `cos_route.py`, act on its line". The table moves into the script's docstring and code. § Commands' queued-ticket paragraph points at the same script.

### 2. Stuck check and restart message: new `cos_restart.py`

Today § Child path "Stuck check" lists the three stuck cases, the wait-check exit rules, the `restarts[stage]` rule, and a restart message with five variants (PR, `ci` mode, spec, build with no PR, cancelled running child, continuation wording). About 3500 characters, all fixed once the model knows the run status, the wait-check result and two lines of judgement.

New `agent-team/scripts/cos_restart.py <PREFIX>-N --run <completed|failed|interrupted|running> --updated-at <ISO> [--marker] [--wait <0|1|2|2twice>] [--step <text>] [--missing <text>] [--now <ISO>]`. It reads state (`stage`, `restarts`, `parentThreadId`, `chiefThreadId`, `pr`), the review mode from `project_config`, and, in `build` or `merge` with a PR, the same PR facts `cos_brief.py pr` prints (by calling its function, not by reimplementing it). It prints:

| Line | Meaning |
|---|---|
| `restart: not-stuck` | No restart, no report line. |
| `restart: send <lane> [cancel]` | The restart message (printed above, filled in), then the `set` op for `restarts[stage]` and the Moving line. `cancel` means `task_cancel(firstTaskId)` first. A continuation ticket gets `restart: continuation <lane>` instead, with the same text. |
| `restart: blocked <why>` | `stage` op to `blocked` with `<why>` in `status`; `comment` it and report it. |
| `restart: unreadable` | The `2twice` wait case on a ticket already restarted: not blocked, add the Cleanup line it prints. |
| exit 2, `restart: cannot <what>` | Bad arguments or unreadable state. |

The model still reads the child (`t3_thread_read`, the wait-check call) and writes the one-line `--step` and `--missing`. The section keeps when to run the check, those two judgement lines and the Rate limit paragraph.

### 3. Todo start order: new `cos_todo.py`

Today § Tick "Todo start" tells the model to drop `agent-skip` tickets and those with an open blocker, sort by priority then oldest `createdAt`, and try the readiness check in that order.

New `agent-team/scripts/cos_todo.py`, two passes on stdin like `pm_hygiene.py drift`:

- First pass: the `list-tickets` result. Prints `get <ID>` for each ticket left after dropping `agent-skip`, in sorted order.
- Second pass (`--relations`): the list plus the `get-ticket` results. Prints `start <ID>` lines, sorted, with blocked tickets dropped, then `todo: none` when nothing is left.

The paragraph becomes: make the one `list-tickets` call, run the script, make its `get` reads, run it again, run § Readiness check and start on each `start` line until one starts, else `project-manager` § Backlog pick.

### 4. Cut prose that restates a script

Keep each script's flags, output lines and exit codes in its docstring only. The skill keeps the action for each line, not its meaning. Places:

- `chief-of-staff/SKILL.md` § Tools: a list of script names with one clause each; the shared exit-code rule said once.
- § Merged check and § Sweep: the parts, their order and the output shapes of `cos_merged_check.py`, `cos_sweep.py`, `cos_ready_check.py`, `cos_parent_check.py`, `cos_review_check.py` and `cos_untracked_check.py`.
- § State file: the ops list (in `cos_state.py`) and the JSON example (moves to `state-keys.md`, which already owns the keys).
- § Commands, the user-check paragraph: what `cos_user_check.py` checks stays in its docstring; the skill keeps which commands use the short words, which use the whole message, and the exit-2 fallback.
- § Tick: the two-call description of `cos_tick.py`.
- `project-manager/SKILL.md`: the output shapes of `pm_hygiene.py` and `cos_rank.py dry`.
- `approvals.md`: the tolerance table that `approval_policy.py` already holds, and what `cos_brief.py pr` prints.

### 5. Say each rule once

From the survey of the Chief of Staff files and the role docs. Each rule stays in its owner; the others point to it with a `§` pointer.

| Rule | Owner |
|---|---|
| Stop rules (failed handoff, retired, successor, `take over`) | `rotation.md`; the intro keeps one line per stop reason |
| Ticket `note` is status only | `state-keys.md` |
| The § Models switch before a spec approval send | SKILL § Models |
| Model per role | SKILL § Models (org-chart, ship-loop § Models and the role doc point to it) |
| Auto-approved spec notice before the queued send | `approvals.md` § Auto-approval |
| Approval paths and what the Chief of Staff trusts | `docs/agents/chief-of-staff.md` § What it trusts |
| "I may not hear when this run ends" | `cos_route.py` (§ 1) |
| Where the sweep runs | SKILL § Sweep |
| `<PREFIX>-N` title match, Linear and Jira untracked drop | SKILL § Sweep (§ Adopt points to it) |
| `Running` repeats, reminder risk level, "found by …" wording, thread link format | SKILL § Report format (and `approvals.md` for the reminder) |
| Team changes go through a ticket and PR | SKILL § Guardrails |
| Observation tickets need the user's approval | `approvals.md` |
| No schedules but the rate-limit wake | SKILL § Guardrails |
| Rotation check is the last call | `rotation.md` |
| Project manager timing, the held rule, Todo is the user's | `project-manager/SKILL.md` |

The child task template's "Never" list stays in full: the child must stand alone.

ship-loop: tighten § Approvals, § Continuation tasks, § Changes requested, § Run endings, § CI waits, § Workflow files and § Phases 1, 2, 5 and 6, and move § Running one phase by hand to `ship-loop/reference.md`. Its gates and the approval checks stay in the skill, word for word where they are a gate.

open-pr: tighten § When to skip open, § Open (Verify, Proof), § Proof, § Create PR, § Differs from the spec, § Primary loop, § Review scope, § Inline review replies, § Forbidden and § Optional.

### 6. Move rarely used text to reference files

- SKILL § Sweep's review-check table and `approve N` on `awaiting-review` (only with teammate review on) to a new `chief-of-staff/review.md`.
- § Adopt to a new `chief-of-staff/adopt.md`, since only `adopt N` reads it.
- The Observe kinds list to `ticket-helper.md` § Observation tickets.
- The `rebuild-relay` plan row's rebuild logic to `startup.md` § State rebuild.
- Legacy notes (the heartbeat row, old `SPEC READY`, `scheduledTaskId`) to `startup.md`.

§ When to read a reference file gets a row for each new file. No heading that another file or a script names is renamed or removed: `cos_tick.py` prints `follow <file> § <section>` lines, and `test_section_pointers.py` checks the rest.

### Size targets

Characters, measured with the `compact_check.py` rule after the build. The PR body lists before, after and delta for every file it touched, the total, and whether each target was met, with the reason for any miss.

| File | Smaller by at least |
|---|---|
| `chief-of-staff/SKILL.md` | 15000 |
| `ship-loop/SKILL.md` | 2500 |
| `open-pr/SKILL.md` | 2000 |
| `project-manager/SKILL.md` | 1500 |
| `chief-of-staff/approvals.md` | 1500 |
| `chief-of-staff/rotation.md` | 1500 |
| `merge-pr/SKILL.md` | 800 |
| `docs/agents/chief-of-staff.md` | 1000 |
| `docs/agents/org-chart.md` | 800 |
| Total of the files `compact_check.py` counts | 15000 (348854 to 333854 or less) |

New reference files count in the total, so moving text out of a skill shows up only in that file's line, not in the total.

### Nothing lost

Before the first cut, the build writes an inventory into the as-built: every approval gate, merge gate, repo invariant, `cos_state.py` op and Chief of Staff user command, each with the file and section that states it. After the cuts it records where each one is now (a file and section, or a script and its test). The PR body says the two lists match, and names any entry that moved into a script with the test that covers it.

### Tests

One table-driven test per new script, on fixture state files and stdin, per `AGENTS.md` § Testing:

- `test_cos_route.py`: one row per caller and stage pair from today's table, plus a full lane, the cap reached, a non-empty queue in the lane, a continuation ticket, the conflict rows with the setting `off` and `on`, and a caller that doesn't apply.
- `test_cos_restart.py`: the three stuck cases, `waiting`, `stalled`, the two unreadable cases, already restarted, a continuation ticket, and the message variants (PR, `ci` mode, spec, build with no PR, cancelled running child).
- `test_cos_todo.py`: `agent-skip` dropped, priority and `createdAt` order, a ticket with an open blocker, a closed blocker, an empty list.

No existing test is edited. `test_section_pointers.py`, `test_call_sites.py` and `test_agent_files.py` must still pass; `test_call_sites.py` gets the new scripts' call sites only through the skill text it already scans.

## Leaves out

- Any change to a rule, gate, lane limit, model default or command.
- `cos_tick.py` (CW-60) and the compacter agent (CW-72). `cos_route.py` imports `cos_tick.LIMITS` without editing the file.
- The sections CW-199 edits (above).
- The vendored `agent-security` and `owasp-security` skills.
- A size check that fails CI on growth.
- A marker parser and a `Running` section builder. Both were candidates; they save little and the marker read is where the model judges a child's last message.

## Calls I made

- **Three new scripts, all in the Chief of Staff: `cos_route.py`, `cos_restart.py`, `cos_todo.py`.** These are the places where the model still works out a fixed answer by hand on most turns. ship-loop and open-pr get prose cuts only, because their one remaining fixed computation, the review gate, is CW-199's.
- **Characters, not bytes,** using the `compact_check.py` count, so the before numbers here differ slightly from the ticket's `wc -c` numbers.
- **Targets are deltas,** so they still hold if CW-199 merges first and changes the two skills' starting size.
- **The total target (15000) is below the SKILL.md target plus the others,** because text moved to reference files still counts in the total.
- **`cos_route.py` imports `cos_tick.LIMITS` and `CAP`** instead of keeping its own copy, so the lane limits stay in one place.
- **`cos_restart.py` calls `cos_brief.py`'s PR function** rather than re-reading the PR, so the restart message and the approval brief show the same verdicts.
- **Two new reference files, `review.md` and `adopt.md`,** instead of growing `ticket-helper.md` or `state-keys.md`. Each is read only on its own command.
- **The child task template stays as it is,** though parts repeat ship-loop: a child must be able to act on it alone.
- **The nothing-lost inventory lives in the as-built and the PR body,** not in a new test. A test over prose would only restate it.

## Touches

None of data, money, auth, user email or migrations. It changes how the Chief of Staff picks a lane, restarts a stuck child and orders Todo, by moving fixed steps into three scripts. No gate changes.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.
- The size table in the PR meets the targets, or says why not.
- Each new script, run against a copy of a real state file, prints what the old prose says for the same ticket.
