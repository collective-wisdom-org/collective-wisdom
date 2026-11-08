# CW-91: Say the GitHub review rule once, and why the reviewers can't request changes formally

**Status:** Draft
**Ticket:** [#91](https://github.com/collective-wisdom-org/collective-wisdom/issues/91)

## Goal

The ticket asked to let the code reviewer and security reviewer logins submit formal changes-requested reviews. Those logins no longer exist: CW-110 (#111) removed the per-agent GitHub users, so every agent, the reviewers included, acts as the one account running `gh`, and that account opens every team PR. GitHub refuses a changes-requested review from a PR's own author, so the feature can't work as written today.

This spec narrows the ticket to what still holds: one clear rule on GitHub reviews, stated the same way everywhere, with the reason, and a check that a human teammate's changes-requested review already moves through the team and clears without an agent approving.

## What I checked

Facts from `main` at `5b800cd`.

- **One account.** `scripts/gh.sh` runs `gh` as the login `user.md` maps to the repo, or the active account. No `AGENT_GH_ROLE`, no reviewer login rows in `project.md`, no `personas.md`. The team's PRs are authored by that account.
- **No reviews from the team.** `cos_approve_pr.py` posts nothing (CW-110). `ship-loop` § Approvals and `merge-pr` § Team mode say "Never submit a GitHub review ... No script or agent in the team submits one." `github-auth.md` § Merge gate says "Nothing in the team submits a GitHub review."
- **Uneven wording.** `open-pr` § Agent review comment loop says "no `gh pr review`, no approve, no request changes", but its § Forbidden (feedback loop) lists only `gh pr review --approve`. `security-review` § Forbidden lists only `--approve`. `code-review.md` § Rules says "Never approve or request changes on GitHub". `security-review.md` (the security reviewer's role doc) does not state the rule. The org chart's Code review row says "Never approves or requests changes on GitHub"; the Security review row says "No".
- **Human changes-requested reviews already work.** `merge_pr.py` `teammate_approval` (with `Require teammate approval` `on`) stops on a teammate's standing changes-requested review and passes once that teammate's newer review approves; the author's own reviews are ignored (`latest_verdicts`). `cos_review_check.py` prints `changes` for a request on the head, and `ship-loop` § Changes requested sends the child back to build, then to `MERGE READY` again; the reviewer clears it by approving or dismissing. With the row `off`, GitHub's own `reviewDecision` `CHANGES_REQUESTED` also routes the ticket the same way. `test_merge_pr.py` and `test_cos_review_check.py` cover these rows.

## Builds

Markdown only. No script, test or config change.

1. **One rule, one wording.** Everywhere the team states it: no agent or script submits a GitHub review of any kind (approve, request changes or comment review; `gh pr review` or the API reviews endpoint). Review findings go in PR issue comments that end in `Verdict:`, which stay the merge gate's input.
   - `open-pr` § Forbidden (feedback loop) and `security-review` § Forbidden: replace the `gh pr review --approve` line with `~/.collective-wisdom/scripts/gh.sh pr review` in any form.
   - `security-review.md` § Security reviewer subagent: add the rule, as `code-review.md` § Rules has it.
   - Org chart Security review row: say it never submits a GitHub review, matching the Code review row.
2. **The reason, written once.** `github-auth.md` § Merge gate, next to "Nothing in the team submits a GitHub review": every agent acts as the account that opens the PR, and GitHub refuses an approve or request-changes review from a PR's author, so a reviewer agent cannot request changes formally. Its `CHANGES NEEDED` comment is the block, and `merge_pr.py` enforces it. Formal reviews come only from people.
3. **How a person's changes-requested review is cleared.** Same section, one or two sentences: a teammate's changes-requested review routes the ticket back to build (`ship-loop` § Changes requested); after the fix it clears when that teammate approves or dismisses it on GitHub. No agent approves or dismisses a review. With `Require teammate approval` `on` the merge waits for that.
4. **Close the ticket's other scope.** The PR says why the rest of the ticket's scope no longer applies (reviewer logins, `AGENT_GH_ROLE`, `personas.md`, the `none` login rule) and points at CW-110.

## Leaves out

- Bringing back separate GitHub accounts for the reviewers so they can request changes formally. That reverses CW-110 and is its own ticket if wanted.
- Any agent dismissing a review. Dismissing a person's review is a merge decision, so it stays with people.
- Changes to `merge_pr.py`, `cos_review_check.py`, `cos_approve_pr.py`, branch protection, CODEOWNERS or required checks.
- Replacing the `Verdict:` comments as the gate's input.

## Testing

`python3 -I -m pytest -q agent-team/scripts` must stay green. No new tests: no script behaviour changes, and the existing `merge_pr.py` and `cos_review_check.py` tables already cover a changes-requested review that is then cleared.

## Calls I made

- **I narrowed the ticket instead of bringing the reviewer accounts back.** You started it with "start 91" without answering the earlier question (close, narrow, or restore the accounts). Restoring accounts would undo CW-110 and needs new GitHub users, so I took the narrow path. If you want formal changes-requested reviews from the reviewers, ask for changes on this spec and I'll write it as "bring back two reviewer accounts" instead.
- **The rule covers every kind of review, not just approvals.** The ticket's wording was "never submit an approval". With one account, a request-changes review is refused anyway and a comment review adds nothing over the PR comment, so "never submit a GitHub review" stays the rule.
- **No agent dismisses a review.** The ticket asked how a stale changes-requested review gets cleared. Today only a person's review can exist, so that person approves or dismisses it.
- **No ticket text edit.** I leave the ticket body as written; the PR explains the narrowing.
