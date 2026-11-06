# Codeowners merge their own PRs past a missing review

**Status:** Shipped
**Shipped:** in PR #0, as specified

## Goal

David and Noah (the two codeowners and repo admins) can merge their own PRs through the Chief of Staff when the only thing stopping the PR is the ruleset's required review from another codeowner. No one else can.

## Change

- `merge_pr.codeowners(run)` reads the user logins on the `*` line of `.github/CODEOWNERS` from `origin/main`.
- `gate`: the signed-in login may be the `Owner login` or a codeowner. When `reviewDecision` is `REVIEW_REQUIRED` and the login is a codeowner, the review check passes and the state must be `BLOCKED` (not `CLEAN`). Checks, review PASS comments, closeout and head gates are unchanged.
- `cos_approve_pr.py` accepts the same logins.
- The ruleset "Required Approved PR by Codeowners to Merge to Main" already lists the admin role as a `pull_request` bypass actor, so GitHub refuses the merge for anyone who is not an admin.

## Not covered

- Live merge with a real bypass; the tests cover the gate only.
