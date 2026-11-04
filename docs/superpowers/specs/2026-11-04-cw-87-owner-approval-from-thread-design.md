# CW-87: Post the owner's approving review when the user approves a merge

**Ticket:** [CW-87](https://github.com/dbeallor/collective-wisdom/issues/87)
**Status:** Shipped
**Shipped:** in PR #89, as specified

## Goal

When the user replies `approve N` on a merge in the Chief of Staff thread, the owner's approving review appears on the PR's current head, so the user no longer has to approve on GitHub as well. One script posts it, and only after it has checked the user's own message itself.

**Security review: look at this on purpose.** This weakens the CW-52 merge gate. Today the proof of a merge approval is a click the owner makes on GitHub. After this change the proof is a `createdBy: "user"` message in the Chief of Staff thread, read from T3's local message store. § Security notes says what that trades.

## Today

Facts from `main` at `273fbf9`, checked 2026-11-04.

- `scripts/merge_pr.py` refuses to merge without branch protection on `main` (`read_protection`) and without an approving review by the `Owner login` on the PR's current head (`owner_approval`: the owner's latest `APPROVED`, `CHANGES_REQUESTED` or `DISMISSED` review must be `APPROVED` on `headRefOid`). It must run from the root checkout, so `project.md` comes from root `main`, not a branch.
- `docs/agents/github-auth.md` § Merge gate says the `approve N` reply "proves nothing" and the owner approves on GitHub by hand.
- `merge-pr` § Team mode and `ship-loop` § Team mode (Relays) say: never submit a GitHub review under any login.
- `chief-of-staff` SKILL § Commands: `approve N` runs `cos_user_check.py latest <own thread id> --after <lastSeenAt>` with the words on stdin. § Send or queue: an `approve N` on a merge runs the head check (`pr view --json headRefOid` against `headSha`), then sends or queues the merge relay. Nothing posts a review.
- `cos_state.py` stamps `lastSeenAt` when a ticket enters `awaiting-merge` and rejects a `set` of it in that stage. `chiefThreadId` is the Chief of Staff's current thread.
- The Chief of Staff runs `./scripts/gh.sh` with `AGENT_GH_ROLE=chief-of-staff`. With no role, `gh.sh` uses the active gh account, which `merge_pr.py` already requires to be the owner and not an agent user.
- The builder user opens the PRs, so the owner can approve them (GitHub refuses an author's own approval).
- `approvals.md` (merge block, reminder line) and `status.md` tell the user "Approve the PR on GitHub, then reply `approve N`".

## Change

### New script: `agent-team/scripts/cos_approve_pr.py`

```
scripts/cos_approve_pr.py [--db PATH] [--file STATE] <PREFIX>-N
```

The only argument the caller picks is the ticket ID. Everything else comes from places the caller can't steer:

- **State** (`.agent-team/state.json` in the root checkout, through `cos_state.load`): the ticket must be in `awaiting-merge` with a `pr` and a full 40-hex `headSha`. `lastSeenAt` and `chiefThreadId` must be set.
- **The user's message**: the script builds the words `approve <N>` (N is the ticket number) and calls `cos_user_check.latest(db, chiefThreadId, words, after=lastSeenAt)` in-process. It goes on only when that returns 0 (the newest user-role message with those words, after the cut-off, has `createdBy` exactly `"user"`). It keeps the printed snippet (first 80 characters of that message) for the review body.
- **gh**, with `AGENT_GH_ROLE` removed from the environment (as `merge_pr.py` does):
  - `gh api user -q .login` must equal the `Owner login` (case folded) and must not be one of the agent logins from `project.md`.
  - `gh pr view <pr> --json state,isDraft,baseRefName,isCrossRepository,headRefOid,reviews`: open, not a draft, based on `main`, not from a fork, and `headRefOid` equal to `headSha`.
- **Run from the root checkout**, checked the same way `merge_pr.py` checks it, so the `Owner login` and agent logins come from root `main`'s `project.md`.

Gates run in this order and the first failure stops the script with nothing posted: root checkout, state, user message, gh login, PR facts, head. Then:

- If `merge_pr.owner_approval(facts)` already passes (the owner's latest verdict review is `APPROVED` on this head), post nothing and exit 0. The user check still ran first, so a hand approval on GitHub plus a verified `approve N` still relays.
- Otherwise post one review:

  ```
  gh api -X POST repos/{owner}/{repo}/pulls/<pr>/reviews -f event=APPROVE -f commit_id=<headSha> -f body=<body>
  ```

  Body, one line: `Approved from the Chief of Staff thread on the user's message "<snippet>" for <PREFIX>-N at head <short SHA>. Posted by scripts/cos_approve_pr.py.`

Output, last line:

- Exit 0: `cos-approve: approved #<pr> at <sha>` or `cos-approve: #<pr> already approved by <owner> at <sha>; nothing posted`.
- Exit 1: `cos-approve: stop <PREFIX>-N: <reason>`, nothing posted. Reasons name the gate: `not run from the root checkout`, `ticket not in awaiting-merge`, `no verified "approve N" from the user since <lastSeenAt>` (with the `not-user …` detail), `gh is signed in as <login>, not the owner`, `PR is a draft`, `PR is closed`, `head <new> is not the approved head <old>`, and so on.
- Exit 2: `cos-approve: cannot <what>` (state unreadable, message store schema changed, a gh read or the POST failed).

Exit 2 from the message store never falls back to a thread read. With no script check, no review is posted.

### Chief of Staff (`chief-of-staff` SKILL.md)

- § Send or queue, `approve N` on a merge: head check, then `python3 scripts/cos_approve_pr.py <PREFIX>-N` with **no** `AGENT_GH_ROLE`, then send or queue the relay. Exit 0: go on. Exit 1 or 2: don't send or queue, keep the stage at `awaiting-merge`, and tell the user under Needs you with the script's last line, adding that they can approve the PR on GitHub by hand and reply `approve N` again.
- The § Commands table row for `approve N` on a merge names the script.
- The § Tools GitHub user bullet: every call runs as `chief-of-staff`, except `cos_approve_pr.py`, which runs on the owner's login because the review must be the owner's. Add the script to the Bash bullet's list.
- The § Models row and the note above § Send or queue's head check: the merge approval is proved by the owner's review, which the script posts after the user check, or the user posts by hand.
- A queued merge approval keeps its place. The review is posted before queueing. If the head moves while it waits, the existing head check withdraws it, and GitHub dismisses the stale approval.

### User-facing lines (`approvals.md`, `status.md`)

- Merge block: `Reply "approve 197" to approve and merge (this posts your approving review on GitHub), or "changes 197: …" to send it back.`
- Reminder line and status row lose "Approve the PR on GitHub, then".

### Rules: the one exception

- `merge-pr` § Team mode and `ship-loop` § Team mode keep "Never submit a GitHub review under any login" for every child and agent. Each adds one sentence: the only exception is the Chief of Staff's `scripts/cos_approve_pr.py` on a verified `approve N`; no other path, script or agent submits a review. The `merge-pr` BLOCKED line after a push says the user replies `approve N` again (or approves on GitHub), not only "approve on GitHub".
- `docs/agents/github-auth.md` § Merge gate: the `approve N` reply now posts the owner's approval through the script after the user check; approving by hand still works. The one-time setup (CODEOWNERS, branch protection with stale approvals dismissed) is unchanged and still required.
- `docs/agents/chief-of-staff.md` (trust paragraph and success line) and `docs/agents/org-chart.md` (the merge sentence): same change in one sentence each.

### Test: `agent-team/scripts/test_cos_approve_pr.py`

One table-driven test with a fake `run`, a temp state file and a temp message store (the shape `test_cos.py` already builds). Rows:

- happy path posts exactly one review, with `event=APPROVE` and `commit_id` equal to `headSha`;
- a repeat on an already approved head posts nothing and exits 0;
- each failed gate posts nothing and exits 1: message by an agent, no message after `lastSeenAt`, wrong words (`approve 870`), ticket not in `awaiting-merge`, gh login is an agent user, gh login isn't the owner, PR draft, PR closed, head moved, not the root checkout;
- a gh read failure exits 2 and posts nothing.

## Security notes

For the security review. These are the trade-offs, not open questions.

1. **What now proves a merge.** Before: the owner's click on GitHub, in their own browser session. After: a row in T3's local SQLite store with `role = 'user'`, `createdBy = "user"` and the text `approve N`, newer than the ticket's `lastSeenAt`. Anything that can write that file, or make T3 record a user-role message, can now get a review posted. That is the same trust spec approvals already rest on (`cos_user_check.py`), now extended to merges.
2. **The script is narrow by rule, not by permission.** The Chief of Staff already runs on a machine where the owner's gh token is the active account. Nothing technical stops an agent with a shell from calling the reviews API directly; CW-52 already relied on the "never submit a review" rule for that. This change keeps the rule for everyone and names one exception. It does not add a new token or permission.
3. **Caller inputs.** Only the ticket ID. The words, thread, cut-off, PR number and head come from state and the message store. `lastSeenAt` is stamped by `cos_state.py` and can't be set in `awaiting-merge`. `headSha` can be `set` by the Chief of Staff, as today; it is the head the merge block showed the user, and the existing head check compares against it.
4. **Wrong words or an old approval.** Matching is on token boundaries (`approve 87` does not match `approve 870`), and `--after lastSeenAt` ignores an approval from an earlier round. An agent message with the same words that is newer than the user's fails closed.
5. **Race with a push.** The review is pinned with `commit_id`. If the head moves between the check and the post, the review lands on the old commit, and `merge_pr.py` refuses it (`approved <old>, head moved`). Branch protection dismisses it as stale.
6. **Review body.** Up to 80 characters of the user's own message go into the body as one `-f` argument, with no shell. The body grants nothing; `merge_pr.py` reads only the review state and commit.
7. **Config from a branch.** The root checkout check keeps a PR from changing the `Owner login` or agent logins the script reads.
8. **Reviews before approval.** The script does not check that code and security reviews are PASS. `merge_pr.py` still requires both before it merges, so an approval on an unreviewed head cannot merge.

## Verify

- Test suite: `python3 -I -m pytest -q agent-team/scripts`.
- No live run against GitHub while building: the build child must not submit a review under any login. The first real run is the user's next `approve N` on a merge, done by the Chief of Staff after this merges and a release is installed. The PR description says so.
- `grep -rn "submit a GitHub review\|submit.*review" agent-team` after the change: every hit either forbids it or names `cos_approve_pr.py` as the only exception.

## Non-goals

- Repository rulesets in `merge_pr.py` (classic branch protection only, as today).
- Changing branch protection, CODEOWNERS or the required checks.
- Posting spec approvals, changes-requested reviews or comments on GitHub.
- Making the PR author the owner.
- A fallback thread read when the message store can't be read.

## Calls I made

- **No thread-read fallback.** Spec approvals fall back to `t3_thread_read` when `cos_user_check.py` exits 2. Here a script check is the whole point, so exit 2 posts nothing and the user approves by hand.
- **The caller passes only the ticket ID.** The script builds `approve <N>` itself and reads the thread, cut-off, PR and head from state, so a confused or injected Chief of Staff can't hand it other words or an older cut-off. A user who types `approve CW-87` instead of `approve 87` fails the check and is told to reply `approve 87`.
- **"Already approved" still needs the user check.** The user check runs first, so a hand approval on GitHub without a verified `approve N` relays nothing, as today.
- **Extra PR gates beyond the ticket:** based on `main` and not from a fork, matching `merge_pr.py`.
- **The script imports `owner_approval` from `merge_pr.py`** so "already approved" means exactly what the merge gate accepts.
- **Must run from the root checkout**, like `merge_pr.py`, so a branch can't change the owner login it trusts.
- **No review-PASS check in the script.** The merge gate already has it; repeating it here would add a second place to keep in sync.
- **No live test.** The rules forbid the build child from submitting a review, so the first real post is the user's next merge approval.
