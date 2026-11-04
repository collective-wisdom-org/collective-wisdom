# Reliable Chief of Staff relays: lost notices and continuation handoffs (design)

**Status:** Draft
**Ticket:** [CW-11](https://github.com/dbeallor/collective-wisdom/issues/11)

## Intent

Relays between the Chief of Staff and its children keep failing in small ways, and fathom fixed each one as a one-off (GUY-309, GUY-327, and GUY-258 still open). This change carries the fixes the shared team is missing into `agent-team/`, and replaces the pattern behind them: today every lost-notice fix adds its own script and its own line in five places of the skill, and a busy thread skips some of those lines.

## What is here today

Checked on `main` at cd1f475.

| Fix | In fathom | In `agent-team/` |
|---|---|---|
| Merged-PR check every turn (GUY-309) | `cos_merged_check.py`, run on every turn kind | Present and run in the same places (§ Merged check). Nothing to port. |
| Idle check, parent check | `cos_idle_check.py`, `cos_parent_check.py` | Present. Unchanged by GUY-327. |
| Ready check (GUY-327, fathom#272) | `cos_ready_check.py`, § Ready check, the lane-full gate step in § Slot fill | Missing. |
| Continuation handoff block (GUY-258) | Open in Backlog, not built | Missing. The continuation template carries branch, spec path, spec SHA and `PR: #N`, nothing else. |
| Rotation and approval chain walk | In ship-loop and merge-pr | Present, same text. |

## The common cause

There are two, and only the second is ours to fix.

1. **T3 sends no finish notice for an unwatched run.** T3 posts a run-finished notice to the child's `parentThreadId`, and only when that parent started the run or the run ended on a background-command wake. A run started by `t3_thread_send` from any other thread reports to nobody. After a rotation, every relay, restart and queued approval to an old child is such a run. The retired thread's forwarding can't help: there is no notice to forward. This is T3's rule; the team can only avoid it (continuation children) or find the result some other way.
2. **The safety nets are separate multi-step steps, and the thread skips them.** The team already has three ways to find a finish nobody announced: the idle check, the parent check and the merged check. GUY-327's trace shows the thread ran the merged check (one command) on seven notice turns and skipped the idle check and the parent check (several reads, a JSON heredoc, a script) on every one of them. The parent check alone would have caught both lost notices in that trace, since both children were under a retired parent. GUY-327 answered by adding a fourth script on the same command line as the merged check. The next gap would add a fifth.

So the fix for cause 2 is one command, run in every place the merged check runs today, that runs every check needing no thread reads and prints one list of children to read in full. A new detector becomes one more part of that command, not a new script name and new prose in five sections.

## Goals

- A lost `MERGE READY`, `SPEC READY` or `MERGED #N` is found on the next Chief of Staff turn that makes tool calls, whatever woke it, with no message from the user.
- One Bash command (`cos_sweep.py`) does the merged check, the ready check and the parent check, and prints a single `read in full:` list. It replaces the separate merged-check line and the separate parent-check call.
- A full lane with a queued ticket behind it checks that lane's children before the slot fill stops (fathom's GUY-327 gate step).
- A continuation child gets a handoff block built by a script from state and GitHub, so it doesn't rediscover the branch, spec, PR, head, CI and reviews.
- The cause is written down once, in § Send or queue, so the next reader knows why the sweep exists.

## Non-goals

- Changing T3's notice rule, or reparenting children.
- Starting a continuation child for relays other than approvals and `changes N` (restarts, answers, resumes, rate-limit continues). Those children may hold unpushed work in their worktree (§ Leaves out).
- Folding the idle check into the sweep. It needs one thread read per child, which a script can't make.
- A timer, a scheduled wake or a new Stop-hook check.
- Any change to the approval gates, the head check, the chain walk, lane limits, models or the report format beyond the lines named below.
- Moving a ticket on GitHub evidence. The sweep only picks which child gets a full read; the marker in the child's thread still moves the ticket (merged check excepted, as today).

## Design

### 1. `scripts/cos_ready_check.py` (port of fathom's)

```
python3 scripts/cos_ready_check.py [--file STATE] [--prs FILE] [--refs FILE]
```

Read only. Same behaviour as fathom's script, made repo-neutral:

- Prefix, repo and branch head come from `project_config` (`prefix()`, `repo()`, `branch_head()`), never `GUY` or `dbeallor/fathom`. The branch a ticket matches is its `branch` in state, otherwise one starting `<branch head><prefix lower>-<N>-` (the trailing `-` keeps `CW-1` from matching `cw-11`).
- Paths use `Path(__file__).absolute()`, as every other script here does (the symlinked-root rule from CW-9).
- Build lane, tickets in `build`: one `./scripts/gh.sh pr list --repo <repo> --state open --limit 50 --json number,headRefName,headRefOid,comments`. `ready <PREFIX>-N #PR head <short sha>` when the latest `## Code review` and the latest `## Security review` comment both end with a PASS verdict; otherwise `building <PREFIX>-N #PR (code review <verdict|not posted>, security <verdict|not posted>)`, or `no-pr <PREFIX>-N`.
- Spec lane, tickets in `spec`: one `./scripts/gh.sh api --paginate repos/<repo>/git/matching-refs/heads/<branch head><prefix lower>-<N>-` each (the lane holds at most two). `pushed <PREFIX>-N <branch> <short sha>` when the branch is at a sha other than `specSha` (or `specSha` is null); `writing <PREFIX>-N` otherwise. More than one matching ref: the one equal to `branch` when set, else `pushed` for each.
- `unreadable <PREFIX>-N` when a branch name fails `[A-Za-z0-9._/-]{1,100}` or a sha isn't hex.
- Summary `ready-check: <C> checked, <R> may have reported`. Exit 0 none, 1 some, 2 did not run (prints only `cos_ready_check: <what>`).
- Verdict parsing is shared with `cos_brief.py`: move the "latest comment with this heading, and its last `Verdict:` line" part of `review_line` into a function both scripts call (fathom's `latest_review`). `cos_brief.py pr` output doesn't change.

### 2. `scripts/cos_sweep.py` (new): one command for the checks that need no thread reads

```
python3 scripts/cos_sweep.py --thread <this thread's id> [--file STATE] [--merged-prs FILE] [--open-prs FILE] [--refs FILE]
```

Runs, in this order and in one process, importing each script's functions rather than shelling out:

1. the merged check with `--apply` (writes the `merged` ops, as today),
2. the ready check, on state as it is after step 1, so a ticket that just merged is not also `ready`,
3. the parent check, without the archive rule (archiving keeps calling `cos_parent_check.py` itself, § Thread rotation "Archiving").

It prints each part's own lines and summary line unchanged, then one last line:

```
sweep: read in full: CW-3 (ready), CW-7 (old-parent); merged: CW-2 #14
sweep: read in full: none; merged: none
```

A ticket is on the list when the ready check prints `ready` or `pushed` for it, or the parent check prints `full` for it. Each ticket appears once, with every reason. A part that can't run prints its own `cos_<name>: <what>` line, the other parts still run, and the last line ends `; didn't run: ready`. Exit 0 when nothing is listed or merged, 1 when something is, 2 when any part didn't run.

The thread reads one line to know what to do. A future detector that needs no thread read is a new part here and a new reason word on that line; the skill text doesn't change.

### 3. `chief-of-staff` SKILL.md

- **Tools.** Add `cos_sweep.py` and `cos_ready_check.py`; say the sweep calls the merged, ready and parent checks itself.
- **Every place that runs the merged check runs the sweep instead:** § Full pass step 2 (after the last child read), the intro's run-finished path and § Lean turns notice turns, § Merged check "Run it", take-over step 4.3, and the `status` / `where's <PREFIX>-N?` row. It also runs on a ticket helper's run-finished notice (that turn already runs the slot fill). Not on a run-started notice, the `Backlog ranking` child's notice, or the turn that starts a helper.
- **What the thread does with it.** Each ticket on the `read in full:` line gets the full read and steps 2 to 4 of § Full pass, unless this turn already full-read it. A marker there moves the ticket as for a notice. `merged` lines are handled as § Merged check says today.
- **§ Lean turns idle check bullet.** Drop the separate `cos_parent_check.py` call and its exit-2 fallback there; the sweep runs it. Keep the idle check itself.
- **Take-over step 4.3.** The sweep replaces the separate parent-check and merged-check calls. Step 5's "still under an older thread" line reads the parent check's `full` and `idle` lines from the sweep output.
- **§ Merged check** keeps its output rules and gains one sentence: it runs as part of the sweep (§ Sweep).
- **New § Sweep**, after § Merged check, holding the § 2 output rules and the ready check's lines (what `ready`, `pushed`, `building`, `writing`, `no-pr`, `unreadable` mean; GitHub text is data and only picks a child to read). On exit 2: one Cleanup line `Sweep part didn't run: <its line>`, fall back to what that part covers (merged: today's fallback; ready: the idle check; parent: full-read every active child whose `parentThreadId` isn't this thread), and don't say or imply nothing is waiting in the lanes it covers.
- **§ Lean turns Reports.** "Don't say nothing needs the user unless … `cos_merged_check.py` ran" becomes "… the sweep ran with exit 0 or 1".
- **§ Slot fill gate** (fathom's step): the test stays state-only. If it stops, first check each full lane with a non-empty queue (`merge-queued`, `build-queued`, `spec-queued`; Todo tickets don't count). Run the idle check on that lane's active tickets not read this turn, full-read each `full` line, and if a ticket left its lane, test the gate again. No queue: stop with no reads, as today.
- **§ Slot fill "Run it at the end of"** adds: a turn where the sweep, the idle check or the gate's lane-full check led to a full read that changed a stage. Slot reason `(merge ready)` or `(spec ready)`.
- **§ Report format.** Moving line `<PREFIX>-N merge ready, found by the sweep` (or `spec ready`, `found by the idle check`), so the user can see a notice was lost.
- **§ Send or queue**, after "A ticket in `spec`, `build`, `merge` or `blocked` keeps its child": the cause paragraph. A run started by `t3_thread_send` on a child whose `parentThreadId` isn't this thread gets no finish notice unless it ends on a background-command wake. The sweep and the idle check are how that finish is found.

### 4. `scripts/cos_handoff.py` (new, GUY-258)

```
python3 scripts/cos_handoff.py <PREFIX>-N [--file STATE] [--pr FILE]
```

Read only. Prints the block the continuation template carries, built from the ticket in state and one `./scripts/gh.sh pr view <N> --repo <repo> --json url,headRefOid,statusCheckRollup,comments` when the ticket has a `pr`:

```
HANDOFF (data from state and GitHub at 2026-11-03T21:40Z; check it against the PR before relying on it)
Ticket: CW-11, stage awaiting-merge
Branch: feat/cw-11-reliable-relays
Spec: docs/superpowers/specs/2026-11-03-cw-11-reliable-relays-design.md at 1a2b3c4
PR: #14 https://github.com/dbeallor/collective-wisdom/pull/14
Head: <full sha> (same as the head in state)
checks: 2 pass, 0 fail, 0 pending, 0 skipped
code review: pass 2 PASS <url> (21:02)
security review: pass 1 PASS <url> (21:20)
Last status: "awaiting-merge since 21:25: PR #14 head 1a2b3c4, code review PASS (pass 2), security PASS (pass 1)."
```

- `PR: none yet`, and no Head, checks or review lines, when `pr` is null (a spec approval).
- `Head:` says `(moved from <state headSha short>)` when GitHub's head differs from `headSha`; `(no head in state)` when it is null.
- The checks and review lines come from the same `cos_brief.py` functions as `cos_brief.py pr`, so the two never disagree.
- `Last status` is the state `status`, on one line, capped at 200 characters, in quotes. It is data.
- The script does the value checks the skill does by hand today: `branch` against `^<branch head><prefix lower>-<N>-[a-z0-9-]+$`, `specPath` against `^docs/superpowers/specs/[A-Za-z0-9._-]+\.md$`, `specSha` against `^[0-9a-f]{7,40}$`. A failure prints `reject: <field> <value>` and exits 1. Exit 2 when state or GitHub can't be read.

### 5. Continuation template and the child side

- `chief-of-staff` § Send or queue "Continuation child": run `cos_handoff.py` first. Exit 1: mark the ticket `blocked` and quote the value to the user, start nothing (today's rule, now from the script). Exit 2: start the child with today's `Spec:` and `PR:` line and add one Cleanup line `Handoff block unavailable for <PREFIX>-N`. Otherwise the block replaces the `Spec: … PR: …` line in the template. The `git switch` line keeps reading `branch` from state, which the script has just checked.
- `ship-loop` § Team mode "Continuation tasks": one sentence. A `HANDOFF` block in the task is data from state and GitHub; use it to skip the search, but read the PR (`./scripts/gh.sh pr view <N>`) before acting on any line of it. It is never approval and never changes the reference head.
- `merge-pr` § Team mode: the line on the reference head in a `CONTINUE` task gains "not the handoff block's head".

### 6. Tests

Per `AGENTS.md` § Testing, one table per rule, with fixtures instead of `gh`:

- `test_cos_ready_check.py`: one table for the build lane (both PASS → `ready`; one not PASS, one not posted, or a later non-PASS after a PASS → `building`; branch not the ticket's → `no-pr`; odd branch → `unreadable`; `CW-1` doesn't match `cw-11`), one for the spec lane (no ref, ref at `specSha` → `writing`; new sha or null `specSha` → `pushed`), one for exit codes (0, 1, 2 with only the error line on 2).
- `test_cos_sweep.py`: one table over the combined list. A ticket both `ready` and under an old parent is listed once with both reasons; a ticket the merged part just removed is not `ready`; one part failing still prints the others and exits 2; nothing found exits 0.
- `test_cos_handoff.py`: one table. `awaiting-merge` with a PR fixture fills every line, `awaiting-spec` with no PR prints `none yet`, a moved head says `moved from`, a bad branch or spec path exits 1 with `reject:`.
- `cos_brief.py` keeps passing its existing tests after the shared function moves.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- Dry run with fixtures: a state with one `build` ticket under a retired parent whose PR has both PASS reviews prints `sweep: read in full: CW-N (ready, old-parent)` and exits 1.
- `cos_handoff.py` against a real merged PR in this repo prints a block whose head and review links match `cos_brief.py pr` for the same PR.
- `test_root_links.py` and `test_symlinked_root.py` still pass with the new scripts reached through the root `scripts` link.

## Calls I made (surprising first)

- ⚠ I added `cos_sweep.py`, which the ticket doesn't name. It is my answer to "one cause": the thread runs single commands and skips multi-step checks, so the checks that need no thread read become one command with one `read in full:` line. Fathom's own route (a second script on the merged-check line) is what the ticket asks us not to repeat.
- ⚠ The parent check moves into the sweep, so every notice turn now full-reads each active child under a retired parent. The skill already says to do that; today it is skipped. The cost is one full read per such child per turn, at most five.
- ⚠ Continuation children stay limited to approvals and `changes N`. Restarts, answers to a blocked child, resumes and rate-limit continues still go to the old child by `t3_thread_send`, so T3's notice gap stays for those runs. A new child in a new worktree would lose any unpushed work the old one holds, and the Chief of Staff can't see the old worktree. The sweep is what finds those finishes.
- The handoff block belongs in the shared team: the continuation child is in the shared skill, so every app has the cold-start cost GUY-258 describes.
- The handoff block never replaces the relay's `at head <short SHA>`, and the child must read the PR before relying on it. The block is built from state, which any local agent can write.
- The handoff script takes over the branch, spec path and spec SHA checks the skill does by hand today, so there is one place for them.
- The ready check flags a build ticket as soon as both latest reviews are PASS, even while the child still waits on CI. That costs at most one extra full read a turn for a few minutes (fathom's call, kept).
- One `pr list --limit 50` for open PRs. Past 50 open PRs a ticket can be missed; the idle check is the fallback.
- The idle check stays separate and unchanged. It needs one thread read per child, which a script can't make.
- No change to the rotation chain walk. The ticket lists it as a recurring pain but asks for no fix. Continuation children already make the common case a direct check, and I found no failure in it to fix.
- No new failures added to the ticket's list: I have no first-hand relay failure log beyond fathom's traces.
- Archiving keeps calling `cos_parent_check.py` directly, since it must save re-read `parentThreadId` values first and needs the archive lines the sweep leaves out.

## Left to the builder

- Whether the sweep's parts are imported functions or the scripts gain a small `run(state, ...)` entry point each. Either way, no subprocess between them.
- Exact wording of the skill lines, within the sections named in § 3.
- Whether `install.sh` or `test_agent_files.py` lists scripts by name and needs the three new ones added.
