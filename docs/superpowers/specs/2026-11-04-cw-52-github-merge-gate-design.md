# CW-52: Put the merge gate on GitHub: branch protection plus an owner review

**Ticket:** [CW-52](https://github.com/dbeallor/collective-wisdom/issues/52)
**Status:** Shipped
**Shipped:** in PR #84, with differences: [as-built](../as-built/2026-11-04-cw-52-github-merge-gate.md)

## Goal

The user proves a merge approval by approving the PR on GitHub, not by a message the merge child has to find by walking thread history. `scripts/merge_pr.py` refuses to merge without an approving review from the owner login on the current head, and branch protection on `main` stops the agent users from merging around it.

## Today

Facts from `main` at `469567f`, checked 2026-11-04.

- `main` has no branch protection (the ticket: `repos/dbeallor/collective-wisdom/branches/main/protection` returns 404).
- `merge_pr.py` `gate()` checks the root checkout, PR state, the gh login (not an agent user), head equals the approved SHA, `CLEAN` mergeability, green checks, the two review comments ending in `Verdict: PASS`, closeout docs and the root checkout. It reads no GitHub review and no branch protection.
- PRs are authored by the builder login (`collective-wisdom-builder`). The owner (`dbeallor`) is not the author, so GitHub lets them approve. The four agent users have write access, so today any of them could approve, and could merge through the API.
- A merge approval is proved in three skills:
  - `ship-loop/SKILL.md` § Team mode **Relays** and **Continuation tasks**: read the approval thread for a `createdBy: "user"` message; when the relay's `Approval in thread:` line names another thread, walk the chain in `ship-loop/reference.md` § Relay chain walk (Moved-to checks, up to 30 hops).
  - `merge-pr/SKILL.md` § Team mode: the same thread read and chain check before merging.
  - `chief-of-staff/SKILL.md` § Send or queue: every spec and merge approval relay carries `Approval in thread:`; a queued approval stores `approvalItemId` and is re-checked with `cos_user_check.py item` before it is sent. `startup.md` § State rebuild and `continuation.md` repeat parts of it.
- The merge block in `chief-of-staff/approvals.md` ends `Reply "approve 197" to merge, or "changes 197: …" to send it back.` The reminder line and `status.md`'s example row say the same.
- `docs/agents/org-chart.md` says the child checks the Chief of Staff thread for a `createdBy: "user"` message before building and before merging.
- CI runs two jobs, `script-tests` and `shellcheck`.

## Change

### Branch protection (the user does this by hand)

No agent changes GitHub settings. The PR adds the steps to `docs/agents/github-auth.md` in a new § Merge gate, written for any app, and the PR description lists them for this repo. The user does them before the first merge after this PR lands:

1. Merge this PR first. It adds `.github/CODEOWNERS` with one line, `* @dbeallor`.
2. Settings → Branches → add a classic branch protection rule for `main`:
   - Require a pull request before merging, with 1 required approval.
   - Dismiss stale pull request approvals when new commits are pushed.
   - Require review from Code Owners. Only the owner's approval then counts; an approval from an agent user does not satisfy the rule.
   - Require status checks to pass: `script-tests` and `shellcheck`. Leave "require branches to be up to date" off.
   - Do not allow bypassing the above settings (enforce for admins).
3. Run the new Verify lines: `./scripts/gh.sh api repos/<owner>/<repo>/branches/main/protection --jq .required_pull_request_reviews.required_approving_review_count` prints `1`.

For an installed app, § Merge gate says the same with `<owner login>` and the app's own required checks, and says the app needs the builder user set up (§ Agent users), because GitHub doesn't let a PR's author approve it.

### `merge_pr.py` gate

Two new reads in `read_facts`: the PR's `reviews` (added to `FIELDS`), and `repos/{owner}/{repo}/branches/main/protection` through `gh.sh`. A 404 is recorded as no protection; any other error is a failed read (exit 2) as today.

The owner is the `Owner login` row of root `main`'s `project.md`, or the running gh login when that row has no backticked value.

Two new checks in `gate()`, after the checks pass and before the review comments, each a one-line stop:

- `main has no branch protection requiring an approving review; set it up per docs/agents/github-auth.md § Merge gate`, when protection is missing or requires fewer than 1 approving review.
- `no approving review by <owner> on head <short SHA>`, when the owner's latest review that is `APPROVED`, `CHANGES_REQUESTED` or `DISMISSED` (comment-only reviews are skipped) is missing, is not `APPROVED`, or was submitted on another commit. When it is `APPROVED` on an older commit, the line ends `; approved <short SHA>, head moved`.

The reviews-stand note (`Head moved to ...`) still lets the agent reviews stand after a main merge. It does not stand in for the owner's approval: a head that moved after the user approved needs a new approval on GitHub.

`merge-pr` § Pre-merge checks names the two checks.

### Skills: the merge path drops the chain walk

- `ship-loop/SKILL.md` § Team mode **Relays** and **Continuation tasks**: the `createdBy: "user"` check, the `Approval in thread:` line and the chain walk apply to spec approvals only. A merge relay is proved by the owner's approving review on GitHub, which `merge_pr.py` checks; the child reads no thread for it. `reference.md` stays, for spec approvals.
- `merge-pr/SKILL.md` § Team mode: replace the thread read and chain-check bullets with one bullet: the explicit-request gate is a `CHIEF OF STAFF:` relay in this thread naming this PR, and the proof is the owner's approving review on the current head, which `merge_pr.py` checks. When the script stops with `no approving review by ...`, stop with `BLOCKED: <the script's last line>`. A push after `MERGE READY` (main merged in) makes the user approve again; the child says so in that `BLOCKED:` line. The `TEAM MODE. CONTINUE` bullet drops "and the chain check above".
- `chief-of-staff/SKILL.md` § Send or queue: the merge approval relay loses its `Approval in thread:` line, and a queued merge approval stores no `approvalItemId` and skips the `cos_user_check.py item` re-check (the head check before sending stays). Spec approvals keep both.
- `chief-of-staff/startup.md` § State rebuild: a rebuilt `merge-queued` ticket sets no `approvalItemId`. `continuation.md`: the queued-approval re-read and the chain-check sentence name spec approvals only.
- `chief-of-staff/approvals.md` merge block: `Approve PR #X on GitHub (<PR URL>), then reply "approve 197" to merge, or "changes 197: …" to send it back.` The reminder line and `status.md`'s example row get the same "approve on GitHub, then" wording. The `approve N` reply still routes the merge child; the Chief of Staff still checks it is the user's (§ Commands), but it no longer proves the merge.
- `docs/agents/org-chart.md`: the child checks the thread before building; before merging, `merge_pr.py` checks the owner's GitHub approval.

### Overlap with open work

- CW-57 (PR #81, in build) edits the chief-of-staff report text, `approvals.md`, `status.md`, `cos_brief.py` and `agent_usage.py`. This PR changes one sentence of the merge block in `approvals.md`, its reminder line and one row of `status.md`, and doesn't touch `cos_brief.py` or `agent_usage.py`.
- CW-72 (spec stage) edits `ship-loop`, `open-pr`, `build-from-plan`, `org-chart` and `docs/agents/README.md`. This PR changes the two `ship-loop` § Team mode bullets above and one `org-chart.md` bullet, and doesn't touch `open-pr`, `build-from-plan` or `README.md`.
- Before building, merge `origin/main` into the branch; again before `MERGE READY` if either has merged.

## Tests

One table-driven test in `agent-team/scripts/test_merge_pr.py` over `gate()`, with `green()` given an owner approval on the head and a protection record. Rows: owner approved on head (passes), approved on an older head (stops), approved by a non-owner login (stops), owner approved then requested changes (stops), no protection (stops), protection with 0 required approvals (stops). Plus one `read_facts` row that turns a 404 on the protection read into "no protection" rather than exit 2.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
- `grep -n "Approval in thread\|reference.md" agent-team/.claude/skills/merge-pr/SKILL.md` finds nothing, and no merge-path sentence in the three skills mentions the Moved-to check.
- After the user sets up protection: `python3 scripts/merge_pr.py <N> <head>` on a PR with PASS reviews and no owner approval prints `merge-pr: stop #N: no approving review by dbeallor on head <sha>`.

## Non-goals

- Spec approvals. They stay in the thread, with the `createdBy: "user"` check and the chain walk.
- Changing GitHub settings from an agent. The user does them.
- `install.sh` and `agent-team/templates/project.md`: the `Owner login` row already exists, and an app's `CODEOWNERS` is the app owner's call.
- Checking the GitHub approval in the Chief of Staff before relaying. The merge child's gate checks it.
- Rulesets. Classic branch protection is enough for one owner.

## Calls I made

- **A head that moves after the user approves needs a new approval on GitHub.** Today the merge child may merge main in after `MERGE READY` and merge on a reviews-stand note with no new word from the user. Stale approvals are dismissed and the gate wants the owner's approval on the current head, so the child now stops with `BLOCKED:` and the user approves again.
- **An app without the builder user can't merge through the gate.** GitHub doesn't let a PR's author approve it, so when PRs are opened as the owner the gate always refuses. § Merge gate says the builder user is required. The alternative, skipping the approval check when the builder row is `none`, keeps the weak path the ticket removes.
- **"Agent users can't approve" uses CODEOWNERS plus "Require review from Code Owners".** A personal repo can't limit who may approve, and the agent users need write access. With code-owner review on, their approvals don't count. The PR adds `.github/CODEOWNERS` (`* @dbeallor`) for this repo only.
- **Enforce for admins, and required checks `script-tests` and `shellcheck`.** The merge runs as the owner, an admin; without enforcement GitHub would let that merge skip the rule. The required checks weren't in the ticket; they make GitHub refuse a red merge too.
- **The gate checks only that protection exists and requires at least one approval.** It doesn't read the code-owner, dismiss-stale or admin settings; the gate's own approval check covers what they guard against for its own merges, and fewer settings checks break less.
- **The `approve N` reply stays, and the Chief of Staff still checks it is the user's.** It routes the merge child and costs nothing; it just no longer proves the merge.
- **`reference.md` § Relay chain walk stays** for spec approvals after a rotation. The ticket says the chain walk goes from three skills; it goes from their merge paths only, since spec approvals stay in the thread.
- **This PR merges under today's gate.** Root `main` runs the old `merge_pr.py`, so this PR's own merge needs no owner approval. Every merge after it needs protection set up first, so the PR description puts the setup steps at the top.
