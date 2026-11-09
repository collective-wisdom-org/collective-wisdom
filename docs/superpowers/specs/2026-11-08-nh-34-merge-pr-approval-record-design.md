# NH-34: Make merge_pr.py check the user's approval itself — Design

**Date:** 2026-11-08  **Ticket:** [NH-34](https://github.com/noahstotland/nohands/issues/34)
**Status:** Shipped
**Shipped:** in PR #264, as specified

## Intent

`merge_pr.py` only compares the PR head with the SHA its caller passes in. The check that the user really wrote `approve N` lives in `cos_approve_pr.py`, which the Chief of Staff runs before relaying. A role that skips the skills and calls `merge_pr.py` directly is stopped by nothing. This change makes `merge_pr.py` confirm the approval on its own, for the head it is about to merge.

## Where the change lives

PR #69 moved this repo to the collective-wisdom v0.2 machine install, and `scripts/merge_pr.py` no longer exists here. The script is `agent-team/scripts/merge_pr.py` in collective-wisdom, which every repo on this Mac runs from `~/.collective-wisdom`. An earlier draft of this spec changed an in-app copy. That copy is gone, so this replaces it, and the change now follows the ticket and the ship loop's Workflow files rule without any waiver.

Three pieces, in order:

1. **A collective-wisdom PR** from `feat/nh-34-merge-pr-approval-record`, built in a separate clone. `~/collective-wisdom` is the live install and stays at its tag. It carries the code, tests and doc edits, plus a copy of this spec for that repo's closeout check, as PR #123 did for NH-29. Code and security reviews run on it. The user merges it, because there is no collective-wisdom root checkout on `main` here for `merge_pr.py` to run from.
2. **This repo's PR** on the same branch name, with this spec and its closeout docs. It links the collective-wisdom PR and has no code.
3. **Taking the change into use is the user's step**: `./tag-release.sh`, then `git checkout v0.N` and `./install.sh` in `~/collective-wisdom`. It changes every repo on this Mac, so no agent runs it. Until then, merges here run v0.2's existing gate.

The ticket's acceptance asks for "an install PR here, with `docs/agents/installed-from.txt` updated". v0.2 has no per-app install and #69 deleted that file, so step 3 stands in for that line.

## Behaviour

After the existing "head equals approved SHA" gate, an open PR must pass the steps below, or `merge_pr.py` stops with `merge-pr: stop #N: <reason>` (exit 1) and nothing changes.

The "record head" is the PR's current head, or its reviewed first parent when `resolved_head` accepts a conflict-resolved head (`Review after conflict resolution` is `off`). The ticket's `headSha` may name either, and the cut-off below uses the commit it names.

1. **Is this a team repo?** If `.agent-team/state.json` does not exist in the root checkout, there is no Chief of Staff and no record to check. The script prints `merge-pr: warn no team state; approval not checked` and goes on with today's gates. This keeps hand runs working in a repo with no team (see Calls I made).
2. **Find the ticket.** Exactly one ticket in the state file has `pr` equal to this PR. None or several: stop.
3. **Stage.** That ticket is in stage `merge`. The Chief of Staff moves it there when it relays the approval, and a withdrawn approval moves it back. A ticket in `merge` with `noApproval: true` (a conflict run with no user approval) is refused, so an older `approve N` can't carry over to it.
4. **Head.** The ticket's `headSha` equals the PR's current head or, for an accepted conflict resolution, its reviewed first parent, in full, whatever SHA the caller passed.
5. **The approval**, either of:
   - **The user's message.** `cos_user_check.latest` on `chiefThreadId`, with the words `approve <ticket number>` and the cut-off below, returns a message with `createdBy: "user"` that isn't negated. An agent's copy of the words fails, as it does today.
   - **The standing auto-approval.** The same rule `cos_approve_pr.py --auto` applies (`Approval risk tolerance` on the merge target branch, or an active No Hands run that started this ticket, plus the approval or hands path, renamed-file, file-count, flag, migration and conflict-note stops) says auto for this PR.

**Cut-off for the message.** It must be newer than the latest of: the record head's commit date and, outside `ci` review mode, the latest code and security review comments the gate already found. So a push after the approval voids it, and so does a new review.

An already merged PR returns before this check, so a repeat run for cleanup still works. The script writes nothing. A state file that exists but can't be read, or a message store that can't be read, exits 2 with `merge-pr: cannot read PR #N: ...`, like other read failures. Neither falls back to letting the merge through.

## How it's built

All in `agent-team/` in collective-wisdom.

- `read_facts` gathers the approval result for open PRs, after the root-checkout fact, using `cos_state` and `cos_user_check`. `gate()` stays free of I/O and reports it after the head check.
- `cos_approve_pr.py` imports `merge_pr`, so `merge_pr` can't import it back. `auto_gate` moves unchanged into `approval_policy.py`, which both can import.
- `cos_approve_pr.py`'s own checks don't change.
- Doc edits, because hand runs change: the `merge_pr.py` docstring's check list, `merge-pr` § Gate, the hand-run lines in `ship-loop` § Approvals, and `github-auth.md` § Merge gate.
- Tests in `test_merge_pr.py`, one table-driven test, with a temporary state file and SQLite store like `test_cos_approve_pr.py`.
  - Passes: a valid `approve N` (including an owner-authored PR), an auto-approved ticket, a conflict-resolved head with the approval on its first parent, no state file.
  - Refuses: no ticket for the PR, wrong stage, `headSha` for another head, no message, a message older than the head commit or a review, `createdBy: "agent"`, a negated message, the auto rule saying no, and a caller passing the current head with no approval.
  - Exits 2 on a corrupt state file.

## Calls I made

- **Moved upstream, reversing the earlier draft.** See Where the change lives. Merging the collective-wisdom PR and running the release are your steps, and the protection starts only after the install.
- **A hand merge in a team repo is refused.** A repo with `.agent-team/state.json` needs the ticket in the team's `merge` stage, so a `merge it` in a separate session stops. Your options there are `approve N` through the Chief of Staff, or GitHub by hand. The ticket asks for this ("whatever SHA the caller passes"), and any bypass flag would be open to the roles this closes off.
- **A repo with no team state keeps working, with a warning.** Hand runs are a supported mode, some with no T3 message store at all, and there is nothing to check against. So deleting the state file skips the check. That is listed under Limits.
- **Auto-approvals pass, though the ticket says only `approve N`.** The ticket predates v0.2's tolerance and No Hands modes. Refusing them would break both, and re-running the same rule means an agent can't get a merge the setting doesn't allow.
- **The approval is checked at the source, with no new record file.** The ticket lets this PR pick the mechanism. A record file or PR comment could be written by any role on this machine, or by anyone using this `gh` login. T3 stamps `createdBy` on your messages, so reading the store needs no new secret and works when you both wrote and approve the PR.
- **`lastSeenAt` is not the cut-off.** `cos_approve_pr.py` uses it, but the Chief of Staff rewrites it on every read of a ticket in `merge`, so it would refuse good approvals. The commit date and GitHub's own comment times don't move.
- **Stage `merge` only, not `awaiting-merge` or `merge-queued`.** The Chief of Staff sends the relay just before writing that stage, so a very fast child could be refused. It would stop with `BLOCKED:` and a resume clears it. I took that over accepting a stage where the approval may have been withdrawn.
- **A Chief of Staff rotation needs a new `approve N`** if it lands between the approval and the merge, because the check reads only the current `chiefThreadId`. `cos_approve_pr.py` already behaves this way before the relay.

## Limits

- This stops a role that ignores the skills. It doesn't stop one that deliberately deletes or edits `state.json`, backdates a commit, or writes to T3's database. Those run as your user on your machine.
- The collective-wisdom PR merges under the old gate, so the new check first runs after the install. No live merge is run as part of this ticket.

## Out of scope

- A new collective-wisdom ticket; this runs under NH-34, as NH-29 did.
- Negated approvals beyond what `cos_user_check` already rejects.
- Changing when the Chief of Staff may approve without your message (NH-22).
- Any change to this app's Swift code.
