# CW-138: A conflict resolution stage that does not restart the review loop

**Ticket:** [CW-138](https://github.com/collective-wisdom-org/collective-wisdom/issues/138)
**Status:** Draft
**Related:** #46

## Goal

Resolving a merge conflict on a PR that is waiting to merge should cost one small child run, not a trip back through the build lane with a full code and security review. Give conflict resolution its own stage and lane. After it, re-review is opt-in and off by default. The merge gate still merges only a head the user approved.

## Today

Facts from `main` at `a9dd73b`, checked 2026-11-05.

- `open-pr` § Primary loop step 1 merges `origin/main` into the branch and resolves clear conflicts; anything unclear is `BLOCKED: <question>`. It only runs while the PR is in the build lane.
- A conflict that shows up once the PR is `awaiting-merge` or `merge-queued` has no home. The Chief of Staff's head check (SKILL.md § Send or queue) sends the head-moved relay to the **build** lane. The child runs both reviews again, because `scripts/pr_diff_delta.py` prints `changed` for a resolution.
- `scripts/merge_pr.py` `stands()` accepts an older review only with a `Head moved to <head> by merging main; ... unchanged since <reviewed>` note and a `same` delta.
- `merge-pr` § Head moved and `merge_pr.py`'s approved-head check void a merge approval on any other head.
- `STAGES` in `scripts/cos_state.py` has `spec`, `build`, `merge` as active stages; the overall cap is 5.

## Design

### The stage and lane

New active stage `conflict` and queue stage `conflict-queued`: a fourth lane, **limit 1**, counted in the overall cap, which becomes 6 (the sum of the lane limits, as the Lanes table already says). It does not use a build or merge slot.

Why its own lane and not the merge slot: a merge in flight changes `main`, so a resolution made at the same time is stale before it is pushed. Why limit 1: each resolution merges the current `main`, so they go one after another, the same reason the merge lane is 1. The merge lane keeps its limit of 1 and its rule that merges run one at a time.

Models: the conflict child runs on Sonnet 5.5, high effort, like build and merge (no switch; it is the ticket's same child thread).

`awaiting-merge` and `blocked` still hold no slot. A `blocked` conflict child resumes into the conflict lane (`resumeStage` `conflict`). Slot fill order becomes merge, conflict, build, spec: a conflicted PR is the one holding up a merge.

### How a ticket gets there

The Chief of Staff routes a ticket to the conflict lane when GitHub says the PR conflicts with `main` (`mergeable` is `CONFLICTING`). It reads that itself; it never takes a child's word for it. Three places:

1. **Approval request.** `scripts/cos_brief.py pr` gains a `conflict: yes` line. When it is there, the Chief of Staff does not ask for approval. It sends the conflict relay (below) through § Send or queue to the conflict lane instead.
2. **Head check** (before a merge approval is sent or queued, and again before a queued one is sent). Besides `headRefOid`, it reads `mergeable`. On `CONFLICTING` it withdraws the approval (`Approval withdrawn at <time>: the PR conflicts with main.`), tells the user under Needs you and sends the conflict relay to the conflict lane. A head that moved for any other reason still goes to the build lane as today.
3. **A merge child that reports `BLOCKED:`.** Before marking the ticket `blocked`, the Chief of Staff reads `mergeable`. On `CONFLICTING` the ticket goes to the conflict lane, not `blocked`.

The sweep does not poll tickets that sit in `awaiting-merge` for conflicts. It is found at the next of the three places. Polling is left out.

Conflicts met before the first `MERGE READY` stay where they are: `open-pr` § Primary loop step 1, in the build lane, before any review exists to restart.

### What the conflict child does

New `open-pr` § Conflict resolution, which step 1 of the Primary loop points to. The relay is `CHIEF OF STAFF: the PR conflicts with main. Resolve it per open-pr § Conflict resolution and report MERGE READY.`

1. Merge `origin/main` into the branch in the worktree and resolve. Resolve only what has one clear answer; anything unclear is `BLOCKED: <question>`, as today.
2. Run the Test command from `project.md`, then push **one merge commit** whose first parent is the head the reviews were posted on. No other commit goes in this run.
3. Wait for CI (`ship-loop` § CI waits).
4. Read `Review after conflict resolution` from `project.md` on `origin/main`:
   - `off` (default): post the note `Head moved to <head> by resolving conflicts with main; reviews from <reviewed> stand.` (full SHAs, as the builder) and stop. No code review, no security review, no docs check.
   - `on`: run the code review, then the security review, on the resolved head, as `open-pr` and `security-review` say. No note.
5. Report `MERGE READY` at the new head. It gets one extra line, `Conflict resolved: <files>; reviews <stand from <short SHA> | rerun and PASS>`.

The run ends at `MERGE READY` like any other, so the Chief of Staff's existing handling moves the ticket `conflict` → `awaiting-merge` and asks for approval. No new run-ending marker.

### The setting

New row in `project.md` and `agent-team/templates/project.md` § Identity, next to the approval risk tolerance:

`Review after conflict resolution (`off` or `on`)` | `off`. Whether a conflict resolution is reviewed again before it can merge. `off`: reviews from before the resolution stand, and the merge asks you to approve the resolved head knowing it was not reviewed. `on`: code and security review run on the resolved head.

Read from `origin/main`, never the working tree, like `Approval risk tolerance`. A missing row means `off` (an installed app that updates keeps today's pattern of one approval, no new review). An unknown value or an unreadable file means `on`: the safe side is to review.

### The merge gate and the approval

**The approval does not carry over.** A conflict resolution is a new head, so the merge approval is void and the user approves the resolved head. `merge-pr` § Head moved, `merge_pr.py`'s approved-head check and `cos_approve_pr.py` do not change. The merge block for a resolved head says so under Risks: the head is a conflict resolution, and whether it was reviewed. That is the point of the opt-in: with it off, the user's approval is the only check on the resolution, so the block says plainly it was not reviewed.

**Auto-approval never covers an unreviewed resolution.** `cos_brief.py pr` prints a `flag: conflict resolution not reviewed` line when the head carries the conflict note (`off`). `cos_approve_pr.py --auto` already refuses on any `flag:` line, so the user decides.

**`merge_pr.py` accepts the conflict note, narrowly.** In `stands()`, a second note form, `Head moved to <head> by resolving conflicts with main; reviews from <reviewed> stand.`, covers the review only when all of these hold; otherwise the review is stale as today:

- the setting on `origin/main` is `off`;
- the note is by the gh login running the merge, and names the current head;
- the head is a merge commit with exactly two parents, the first being `<reviewed>`; and
- the head is the only commit after `<reviewed>` in the PR (the `commits` list).

That bounds what went in unreviewed to one merge commit of `main` plus its conflict edits. The old `same`-delta note for a clean `main` merge is untouched.

### Skills and docs

- `open-pr`: new § Conflict resolution; Primary loop step 1 points to it for conflicts found after `MERGE READY` and keeps its text for conflicts before it.
- `ship-loop`: § Phases 4 gets the conflict child's path and the extra `MERGE READY` line, and notes the `Review after conflict resolution` setting. § Phase gates adds the conflict note beside the main-merge exception. The head-moved line in § Phases 5 and § Approvals stay.
- `merge-pr`: § Head moved names a conflict fix and says the user approves the resolved head; the conflict stage exists for that.
- `chief-of-staff`: § Lanes table (new row, overall cap 6), the stages list, § Full pass (conflict child read like merge), § Send or queue (relay, caller table rows, head check, `MERGE READY` from `conflict`), § Slot fill (order, queue), § Report format (Moving by lane), `status.md`.
- `approvals.md`: the merge block's Risks line and the `Conflict resolved:` line.
- `org-chart.md` lane diagram and `github-auth.md`'s merge paragraph (the resolved head needs a new approval).
- Install copy: nothing extra. `install.sh` copies everything under `agent-team/`; the template gets the new row, and an existing app without the row gets `off`.

### Scripts

- `cos_state.py`: add `conflict` and `conflict-queued` to `STAGES`, `conflict` to `ACTIVE`, the lane loop in `show`.
- `project_config.py`: `review_after_conflict()` reading the row from `origin/main`.
- `merge_pr.py`: the conflict note in `stands()`.
- `cos_brief.py`: `conflict: yes` and the `flag:` line.

### Tests

Table-driven, one per rule, per `AGENTS.md` § Testing:

- `test_merge_pr.py`: the conflict note covers a stale review only when all four conditions hold, one row per way to fail (setting `on`, note by another login, note names another head, two commits after the reviewed head, head not a merge commit, first parent is not the reviewed head), and the old main-merge note still works.
- `test_project_config.py`: missing row `off`, `on` and `off` read, unknown or unreadable `on`.
- `cos_state` tests: the new stages are accepted, a `conflict-queued` ticket needs `pendingRelay`, a `blocked` conflict ticket records `resumeStage`.
- `cos_brief` test: `conflict: yes` and the `flag:` line appear for the right PR states.

No tests for the skill prose.

## Acceptance, mapped

- A conflicted PR is resolved in the conflict lane and takes no build slot: the Lanes table and the head check above.
- Setting `off`: no review runs after a resolution. `on`: both run on the resolved head: § What the conflict child does, step 4.
- An unclear resolution still stops with `BLOCKED: <question>`: step 1.
- The merge gate after a head move is stated in `merge-pr`, `ship-loop` and `github-auth.md`, and `merge_pr.py` enforces it with the tests above.

## Left out

- The clean `main` merge exception that uses `pr_diff_delta.py`.
- What the code review and security review check.
- Polling `awaiting-merge` tickets for conflicts.
- A per-ticket choice of re-review. The setting is repo-wide.
- Carrying a merge approval over to a resolved head.

## Calls I made

Surprising first.

- **The user still approves the resolved head.** The ticket allowed either keeping the "approved head" rule or changing it. I kept it: no gate script changes for approvals, and the merge block tells the user the resolution was not reviewed.
- **With the setting off, `merge_pr.py` merges a head whose only unreviewed change is one merge commit.** That is a new way for unreviewed code to reach `main`, bounded to a single merge commit of `main` into the branch by the four conditions above. I chose it because the ticket's acceptance asks for no review by default.
- **Auto-approval never applies to an unreviewed resolution.** Not in the ticket; added because the user's approval is the only check left.
- **Its own lane with limit 1, overall cap 6**, not the merge slot and not a build slot.
- **Missing row means `off`, unknown or unreadable means `on`.** Opposite fail-directions: a missing row is an app that has not updated its template, an unreadable one is an error.
- **No new run-ending marker.** The conflict child ends at `MERGE READY`.
- **The Chief of Staff finds conflicts at three points, not by polling.**
- **A conflict before the first `MERGE READY` stays in the build lane.**
