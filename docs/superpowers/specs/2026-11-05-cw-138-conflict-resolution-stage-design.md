# CW-138: A conflict resolution stage that does not restart the review loop

**Ticket:** [CW-138](https://github.com/collective-wisdom-org/collective-wisdom/issues/138)
**Status:** Draft
**Related:** #46

## Goal

Resolving a merge conflict on a PR that is waiting to merge should cost one small child run, not a trip back through the build lane with a full code and security review. Give conflict resolution its own stage and lane. After it, re-review is opt-in and off by default. With it off, a PR the user already approved for merge is merged by the conflict stage itself, with no second approval. The gate change this needs is explicit and narrow (§ The merge gate and the approval).

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
2. **Head check** (before a merge approval is sent or queued, and again before a queued one is sent). Besides `headRefOid`, it reads `mergeable`. On `CONFLICTING` the approval is **kept** when the setting is `off` (the conflict relay carries it, below) and **withdrawn** when it is `on` (`Approval withdrawn at <time>: the PR conflicts with main.`, the user is told under Needs you, and the user approves again after the reviews). Either way the ticket goes to the conflict lane. A head that moved for any other reason still goes to the build lane as today.
3. **A merge child that reports `BLOCKED:`.** Before marking the ticket `blocked`, the Chief of Staff reads `mergeable`. On `CONFLICTING` the ticket goes to the conflict lane, not `blocked`, with its approval carried when the setting is `off`.

The sweep does not poll tickets that sit in `awaiting-merge` for conflicts. It is found at the next of the three places. Polling is left out.

Conflicts met before the first `MERGE READY` stay where they are: `open-pr` § Primary loop step 1, in the build lane, before any review exists to restart.

### What the conflict child does

New `open-pr` § Conflict resolution, which step 1 of the Primary loop points to. There are two relays. Without an approval (point 1, or an approval the setting `on` withdrew): `CHIEF OF STAFF: the PR conflicts with main. Resolve it per open-pr § Conflict resolution and report MERGE READY.` With an approval to carry (points 2 and 3, setting `off`): `CHIEF OF STAFF: the PR conflicts with main. The user approved the merge at head <short SHA>. Resolve it per open-pr § Conflict resolution and merge.` The second is sent only for an approval the Chief of Staff already verified with `scripts/cos_approve_pr.py` (or `--auto`) at that head, and it names that head.

1. Merge `origin/main` into the branch in the worktree and resolve. Resolve only what has one clear answer; anything unclear is `BLOCKED: <question>`, as today.
2. Run the Test command from `project.md`, then push **one merge commit** whose first parent is the head the reviews were posted on. No other commit goes in this run.
3. Wait for CI (`ship-loop` § CI waits).
4. Read `Review after conflict resolution` from `project.md` on `origin/main`:
   - `off` (default): post the note `Head moved to <head> by resolving conflicts with main; reviews from <reviewed> stand.` (full SHAs, as the builder). No code review, no security review, no docs check.
   - `on`: run the code review, then the security review, on the resolved head, as `open-pr` and `security-review` say. No note.
5. Then one of two endings:
   - **The relay carried an approval and the setting is `off`:** run `merge-pr` with the relay's head as the approved head. `scripts/merge_pr.py` accepts the resolved head under the rule below. The run ends `MERGED #N`, like a merge child's.
   - **Otherwise:** report `MERGE READY` at the new head, with one extra line, `Conflict resolved: <files>; reviews <stand from <short SHA> | rerun and PASS>`. The Chief of Staff moves the ticket `conflict` → `awaiting-merge` and asks for approval as usual.

No new run-ending marker. In a hand run the same holds: the user's approval after `MERGE READY` carries to the resolved head when the setting is `off`.

### The setting

New row in `project.md` and `agent-team/templates/project.md` § Identity, next to the approval risk tolerance:

`Review after conflict resolution (`off` or `on`)` | `off`. Whether a conflict resolution is reviewed again before it can merge. `off`: reviews from before the resolution stand, and a merge you already approved goes ahead on the resolved head without asking again. `on`: code and security review run on the resolved head, and you approve it again.

Read from `origin/main`, never the working tree, like `Approval risk tolerance`. A missing row means `off` (an installed app that updates keeps today's pattern of one approval, no new review). An unknown value or an unreadable file means `on`: the safe side is to review.

### The merge gate and the approval

**This changes the rule that the merged head is the approved head.** Until now any other head voided the approval. After this ticket, with the setting `off`, the approval of head H also covers a **resolved head** H' that is exactly one merge commit on top of H: H' has two parents, the first is H, and H' is the only commit after H in the PR. The user approved H and its reviews. H' adds only a merge of `main` and the conflict edits. Any other head is still `BLOCKED: head moved after approval`. With the setting `on`, nothing changes from today: the user approves the resolved head again.

How it is enforced:

- `scripts/merge_pr.py`: the approved-head check passes when the head equals the approved head, or is a resolved head of it under the rule above with the setting `off` read from `origin/main` and the note below present. The review check (`stands()`) accepts the same note for H'. A new test pins every way the rule fails.
- The note is `Head moved to <H'> by resolving conflicts with main; reviews from <H> stand.`, by the gh login running the merge, naming the current head.
- `scripts/cos_approve_pr.py` is not involved: the Chief of Staff verified the user's message at H before the conflict relay, and the conflict child merges without a second relay. `merge_pr.py` is the gate that stays in the path.
- `merge-pr` § Head moved, `ship-loop` § Approvals and `github-auth.md` state the exception.

**A conflict found before any approval** (point 1, an unapproved ticket) has nothing to carry. The child reports `MERGE READY` at H' and the user approves H' as today. With the setting `off`, the merge block says the resolution was not reviewed.

**Auto-approval never covers an unreviewed resolution.** `cos_brief.py pr` prints `flag: conflict resolution not reviewed` when the head carries the conflict note, and `cos_approve_pr.py --auto` already refuses on any `flag:` line. This matters only for the `MERGE READY` path above.

**One merge at a time.** The conflict child merges from the conflict slot, outside the merge lane's slot. If a merge child merges first, `main` moves; this PR may conflict again, and `merge_pr.py` stops (it needs `MERGEABLE` and `CLEAN`, and merges with the head SHA as a guard). The child reports `BLOCKED: <why>` and the Chief of Staff's routing runs again. It repeats at most as often as `main` moves.

### Skills and docs

- `open-pr`: new § Conflict resolution; Primary loop step 1 points to it for conflicts found after `MERGE READY` and keeps its text for conflicts before it.
- `ship-loop`: § Phases 4 gets the conflict child's path and the extra `MERGE READY` line, and notes the setting. § Phase gates adds the conflict note beside the main-merge exception. § Phases 5 and § Approvals state the resolved-head exception to `BLOCKED: head moved after approval`.
- `merge-pr`: § Head moved gets the resolved-head exception, and the conflict stage's merge path is a `merge-pr` run.
- `chief-of-staff`: § Lanes table (new row, overall cap 6), the stages list, § Full pass (conflict child read like merge), § Send or queue (both relays, caller table rows, head check that keeps or withdraws the approval, `MERGE READY` and `MERGED #N` from `conflict`), § Slot fill (order, queue), § Report format (Moving by lane), `status.md`.
- `approvals.md`: the merge block's Risks line and the `Conflict resolved:` line.
- `org-chart.md` lane diagram and `github-auth.md`'s merge paragraph (the resolved head needs a new approval).
- Install copy: nothing extra. `install.sh` copies everything under `agent-team/`; the template gets the new row, and an existing app without the row gets `off`.

### Scripts

- `cos_state.py`: add `conflict` and `conflict-queued` to `STAGES`, `conflict` to `ACTIVE`, the lane loop in `show`.
- `project_config.py`: `review_after_conflict()` reading the row from `origin/main`.
- `merge_pr.py`: the resolved-head exception in the approved-head check and the conflict note in `stands()`.
- `cos_brief.py`: `conflict: yes` and the `flag:` line.

### Tests

Table-driven, one per rule, per `AGENTS.md` § Testing:

- `test_merge_pr.py`: a resolved head passes the approved-head check and covers the stale reviews only when every condition holds, one row per way to fail (setting `on`, note by another login, note names another head, two commits after the approved head, head not a merge commit, first parent is not the approved head, no note), and the old main-merge note and a plain wrong head still behave as today.
- `test_project_config.py`: missing row `off`, `on` and `off` read, unknown or unreadable `on`.
- `cos_state` tests: the new stages are accepted, a `conflict-queued` ticket needs `pendingRelay`, a `blocked` conflict ticket records `resumeStage`.
- `cos_brief` test: `conflict: yes` and the `flag:` line appear for the right PR states.

No tests for the skill prose.

## Acceptance, mapped

- A conflicted PR is resolved in the conflict lane and takes no build slot: the Lanes table and the head check above.
- Setting `off`: no review runs after a resolution, and an approved PR is merged by the conflict stage. `on`: both reviews run on the resolved head and the user approves it again: § What the conflict child does, steps 4 and 5.
- An unclear resolution still stops with `BLOCKED: <question>`: step 1.
- The merge gate after a head move is stated in `merge-pr`, `ship-loop` and `github-auth.md`, and `merge_pr.py` enforces it with the tests above.

## Left out

- The clean `main` merge exception that uses `pr_diff_delta.py`.
- What the code review and security review check.
- Polling `awaiting-merge` tickets for conflicts.
- A per-ticket choice of re-review. The setting is repo-wide.
- Carrying an approval over in any other case: setting `on`, or a head that is not a single merge commit on the approved head.

## Calls I made

Surprising first.

- **An approval of H carries to a resolved head H' when the setting is `off`.** The ticket allowed either; you asked for the merge to happen without asking again. It is bounded to one merge commit on top of the approved head and checked in `merge_pr.py`. With `on`, or with no approval yet, the user approves H' as before.
- **Unreviewed code can now reach `main` after a merge approval.** It is one merge commit of `main` into the branch plus its conflict edits, and the user's approval did not see it. This is the cost of the opt-out, off by default per the ticket.
- **Auto-approval never applies to an unreviewed resolution.** Not in the ticket; added for the `MERGE READY` path.
- **Its own lane with limit 1, overall cap 6**, not the merge slot and not a build slot.
- **Missing row means `off`, unknown or unreadable means `on`.** Opposite fail-directions: a missing row is an app that has not updated its template, an unreadable one is an error.
- **No new run-ending marker.** The conflict child ends at `MERGED #N` or `MERGE READY`.
- **The conflict child merges from the conflict slot**, not by handing back to the merge lane. A second conflict from a racing merge goes round the same route.
- **The Chief of Staff finds conflicts at three points, not by polling.**
- **A conflict before the first `MERGE READY` stays in the build lane.**
