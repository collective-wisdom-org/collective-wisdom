# CW-138: Resolve merge conflicts in the merge lane without restarting the review loop

**Ticket:** [CW-138](https://github.com/collective-wisdom-org/collective-wisdom/issues/138)
**Status:** Draft
**Related:** #46

## Goal

Resolving a merge conflict on a PR that is waiting to merge should cost one short child run, not a trip back through the build lane with a full code and security review. Give conflict resolution its own stage in the merge lane. Re-review after it is opt-in and off by default. With it off, a PR the user already approved is merged by that stage with no second approval. The gate change this needs is explicit and narrow (§ The merge gate and the approval).

## Today

Facts from `main` at `a9dd73b`, checked 2026-11-05.

- `open-pr` § Primary loop step 1 merges `origin/main` into the branch and resolves clear conflicts; anything unclear is `BLOCKED: <question>`. It only runs in the build lane, before the first `MERGE READY`.
- A conflict found once the PR is `awaiting-merge`, `merge-queued` or `merge` has no home. The Chief of Staff's head check (SKILL.md § Send or queue) sends the head-moved relay to the **build** lane, which runs both reviews again, because `scripts/pr_diff_delta.py` prints `changed` for a resolution.
- `scripts/merge_pr.py` `stands()` accepts an older review only with a `Head moved to <head> by merging main; ... unchanged since <reviewed>` note and a `same` delta.
- `merge-pr` § Head moved and `merge_pr.py`'s approved-head check void a merge approval on any other head.
- The merge lane has limit 1 (SKILL.md § Lanes): merges run one at a time.

## Design

### No new lane and no new stage

Conflict resolution runs in the **merge lane**, in the existing `merge` stage, on the ticket's own child. It uses the merge slot, so it can't overlap a merge. A resolve-and-merge also can't race another merge into a second conflict. `cos_state.py`, the lane limits and the overall cap do not change. A ticket reaches the stage the way any ticket reaches the merge lane: § Send or queue, with a different relay.

The setting decides the lane:

- **`Review after conflict resolution` is `off`** (default): the merge lane, as above.
- **`on`**: the build lane, as today. The resolution is reviewed again, which is long, so it must not hold the one merge slot. The only change is the relay text (below). The approval is withdrawn and the user approves the resolved head again after the reviews.

### How a ticket gets there

The Chief of Staff routes on GitHub's word, never a child's: `./scripts/gh.sh pr view <N> --json mergeable` returns `CONFLICTING`. Three places:

1. **Approval request.** `scripts/cos_brief.py pr` gains a `conflict: yes` line. When it is there, the Chief of Staff does not ask for approval. It sends the conflict relay through § Send or queue, to the merge lane (`off`) or the build lane (`on`).
2. **Head check** (before a merge approval is sent or queued, and again before a queued one is sent). Besides `headRefOid`, it reads `mergeable`. On `CONFLICTING` and `off`, the approval is **kept** and carried in the relay to the merge lane. On `on`, it is withdrawn (`Approval withdrawn at <time>: the PR conflicts with main.`), the user is told under Needs you, and the relay goes to the build lane. A head that moved for any other reason goes to the build lane as today.
3. **A merge child that reports `BLOCKED:`.** Before marking the ticket `blocked`, the Chief of Staff reads `mergeable`. On `CONFLICTING` and `off`, the child still holds the merge slot, so it gets the conflict relay with its approval at once (no slot check, as the stuck-check restart). On `on`, the relay goes to the build lane.

The sweep does not poll `awaiting-merge` tickets for conflicts; a conflict is found at the next of the three places. Conflicts met before the first `MERGE READY` stay in `open-pr` § Primary loop step 1.

Relays:

- Without an approval to carry: `CHIEF OF STAFF: the PR conflicts with main. Resolve it per open-pr § Conflict resolution and report MERGE READY.`
- With an approval to carry (`off`, points 2 and 3): `CHIEF OF STAFF: the PR conflicts with main. The user approved the merge at head <short SHA>. Resolve it per open-pr § Conflict resolution and merge.` Sent only for an approval the Chief of Staff already verified with `scripts/cos_approve_pr.py` (or `--auto`) at that head, and it names that head.

The caller table in § Send or queue gets the rows.

### What the child does

New `open-pr` § Conflict resolution; Primary loop step 1 points to it.

1. Merge `origin/main` into the branch in the worktree and resolve. Resolve only what has one clear answer; anything unclear is `BLOCKED: <question>`, as today.
2. Run the Test command from `project.md`, then push **one merge commit** whose first parent is the head the reviews were posted on. No other commit goes in this run.
3. Wait for CI (`ship-loop` § CI waits).
4. Read the setting from `project.md` on `origin/main`.
   - `off`: post the note `Head moved to <head> by resolving conflicts with main; reviews from <reviewed> stand.` (full SHAs, as the builder). No code review, security review or docs check.
   - `on` (a build-lane child): run the code review, then the security review, on the resolved head, as `open-pr` and `security-review` say. No note.
5. Ending:
   - **Relay carried an approval, setting `off`:** run `merge-pr` with the relay's head as the approved head. The run ends `MERGED #N`.
   - **Otherwise:** report `MERGE READY` at the new head, with one extra line, `Conflict resolved: <files>; reviews <stand from <short SHA> | rerun and PASS>`. The Chief of Staff moves the ticket to `awaiting-merge` and asks for approval as usual.

No new run-ending marker. In a hand run the same holds: the user's approval after `MERGE READY` carries to the resolved head when the setting is `off`.

### The setting

New row in `project.md` and `agent-team/templates/project.md` § Identity, next to the approval risk tolerance:

`Review after conflict resolution (`off` or `on`)` | `off`. Whether a conflict resolution is reviewed again before it can merge. `off`: reviews from before the resolution stand, and a merge you already approved goes ahead on the resolved head without asking again. `on`: code and security review run on the resolved head, and you approve it again.

This repo's own `docs/agents/project.md` gets the row set to `off`, written out rather than left to the default, so collective-wisdom never reruns reviews after a conflict resolution. It takes effect once this PR is on `main`.

Read from `origin/main`, never the working tree, like `Approval risk tolerance`. A missing row means `off`, so an installed app that updates keeps a single approval. An unknown value or an unreadable file means `on`: the safe side is to review.

### The merge gate and the approval

**This changes the rule that the merged head is the approved head.** Until now any other head voided the approval. With the setting `off`, the approval of head H also covers a **resolved head** H' that is exactly one merge commit on top of H: H' has two parents, the first is H, and H' is the only commit after H in the PR. The user approved H and its reviews; H' adds only a merge of `main` and the conflict edits. Any other head is still `BLOCKED: head moved after approval`. With `on`, nothing changes from today.

Enforced in `scripts/merge_pr.py`:

- The approved-head check passes when the head equals the approved head, or is a resolved head of it with the setting `off` (from `origin/main`) and the note above present.
- `stands()` accepts the same note for H'. The note must be by the gh login running the merge and name the current head.
- `scripts/cos_approve_pr.py` is not involved: the Chief of Staff verified the user's message at H before the relay, and the child merges without another.
- `merge-pr` § Head moved, `ship-loop` § Approvals and `github-auth.md` state the exception.

**A conflict found before any approval** has nothing to carry. The child reports `MERGE READY` at H' and the user approves H' as today. With `off`, the merge block says the resolution was not reviewed.

**Auto-approval never covers an unreviewed resolution.** `cos_brief.py pr` prints `flag: conflict resolution not reviewed` when the head carries the conflict note; `cos_approve_pr.py --auto` already refuses on any `flag:` line.

### Skills and docs

- `open-pr`: new § Conflict resolution; step 1 points to it for conflicts found after `MERGE READY`.
- `ship-loop`: § Phases 4 and 5 and § Approvals get the conflict child's path, the extra `MERGE READY` line and the resolved-head exception; § Phase gates adds the conflict note beside the main-merge exception.
- `merge-pr`: § Head moved gets the exception; the conflict path is a `merge-pr` run.
- `chief-of-staff`: § Send or queue (both relays, caller rows, the head check), § Full pass (the `BLOCKED:` check), `approvals.md` (the `conflict: yes` handling and the merge block's Risks line).
- `github-auth.md`'s merge paragraph; `org-chart.md` where it says the head-moved path.
- Install copy: nothing extra. `install.sh` copies everything under `agent-team/`; the template gets the new row.

### Scripts

- `docs/agents/project.md`: the new row, `off`.
- `project_config.py`: `review_after_conflict()`.
- `merge_pr.py`: the resolved-head exception in the approved-head check and the conflict note in `stands()`.
- `cos_brief.py`: `conflict: yes` and the `flag:` line.

### Tests

Table-driven, one per rule (`AGENTS.md` § Testing):

- `test_merge_pr.py`: a resolved head passes the approved-head check and covers the stale reviews only when every condition holds, one row per way to fail (setting `on`, note by another login, note names another head, two commits after the approved head, head not a merge commit, first parent is not the approved head, no note). The old main-merge note and a plain wrong head behave as today.
- `test_project_config.py`: missing row `off`, `on` and `off` read, unknown or unreadable `on`.
- `cos_brief` test: `conflict: yes` and the `flag:` line for the right PR states.

No tests for skill prose.

## Acceptance, mapped

- A conflicted PR is resolved in the merge lane and takes no build slot (setting `off`): § No new lane.
- `off`: no review runs after a resolution, and an approved PR is merged by that stage. `on`: both reviews run on the resolved head and the user approves it again: § What the child does, steps 4 and 5.
- An unclear resolution stops with `BLOCKED: <question>`: step 1.
- The merge gate after a head move is stated in `merge-pr`, `ship-loop` and `github-auth.md`, and enforced and tested in `merge_pr.py`.

## Left out

- The clean `main` merge exception that uses `pr_diff_delta.py`.
- What the code review and security review check.
- Polling `awaiting-merge` tickets for conflicts.
- A per-ticket choice of re-review. The setting is repo-wide.
- A new lane or stage.
- Carrying an approval in any other case: setting `on`, or a head that isn't a single merge commit on the approved head.

## Calls I made

Surprising first.

- **This repo's row is `off`**, as you asked. It is the default too, but the row is written out so the choice is visible.

- **Unreviewed code can now reach `main` after a merge approval, when the setting is `off`.** It is one merge commit of `main` into the branch plus its conflict edits, which the user didn't see. The gate rule "the merged head is the approved head" gets this one exception, enforced in `merge_pr.py`.
- **With the setting `on`, a conflict goes to the build lane as today**, not the merge lane, so a long review doesn't hold the only merge slot. The approval is withdrawn there.
- **The resolution holds the merge slot.** A resolve-and-merge is short, and it means merges stay one at a time.
- **A conflict with no approval yet also takes a merge slot (setting `off`)** for the short resolve run, then the ticket returns to `awaiting-merge`.
- **Auto-approval never covers an unreviewed resolution.** Not in the ticket; added for the `MERGE READY` path.
- **A missing setting row means `off`; an unknown value or an unreadable file means `on`.**
- **No new run-ending marker.** The child ends at `MERGED #N` or `MERGE READY`.
- **Conflicts are found at three points, not by polling.**
