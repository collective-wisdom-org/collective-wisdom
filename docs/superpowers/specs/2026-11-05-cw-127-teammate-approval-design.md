# CW-127: Require a teammate's GitHub approval and GitHub's required reviews before merge

**Ticket:** [CW-127](https://github.com/collective-wisdom-org/collective-wisdom/issues/127)
**Status:** Shipped
**Shipped:** in PR #PRNUM, as specified

## Goal

A repo can turn on a rule that `scripts/merge_pr.py` merges only after a teammate (any GitHub user other than the PR author) approved the PR on its current head. Whatever the setting, when GitHub itself says the PR still needs a required review, the gate says who it is waiting on instead of a generic `not mergeable` line.

The user's `approve N` stays required. A teammate's approval adds to it and never replaces it. No agent or script submits a review.

## Today

Facts from `main` at `d3df944`, checked 2026-11-05.

- `agent-team/scripts/merge_pr.py` reads the PR with `FIELDS` (state, draft, mergeability, head, base, checks, comments, commits, files, merge commit, fork flag, body). It reads no `author`, `reviews`, `reviewDecision` or `reviewRequests`.
- `gate()` checks, in order: root checkout, owner login, state, draft, fork, base `main`, approved head, `mergeable`/`mergeStateStatus` (`not mergeable: mergeable X, state Y`), checks, review comments, closeout, proof, root `main`.
- When branch protection, a ruleset or CODEOWNERS still requires a review, GitHub reports `mergeStateStatus` `BLOCKED`, so the gate stops with `not mergeable: mergeable MERGEABLE, state BLOCKED` and names nobody.
- Every PR the team opens is authored by the owner login (`docs/agents/github-auth.md`), and GitHub never lets an author approve their own PR. So "a user other than the PR author" means a teammate.
- `gh pr view --json author,reviews,reviewDecision,reviewRequests` on PR #132 (gh 2.98.0) returns `reviewDecision: ""`, `reviews: []`, `reviewRequests: []` when there are none. Each review has `author.login`, `state` (`APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED`, `PENDING`), `submittedAt` and `commit.oid`.
- `MERGE READY` (`ship-loop` § Team mode) and the Chief of Staff's merge block (`chief-of-staff/approvals.md`) say nothing about GitHub reviews.

## Change

### `project.md` row

`agent-team/templates/project.md` § Git and GitHub gets a row after `Owner login`:

```
| Require teammate approval (`on` or `off`) | `off`. When on, merge_pr.py also needs an approving GitHub review on the current head from someone other than the PR author. A missing row means off |
```

`read_facts` stores `project_config.value("Require teammate approval")` in `f["teammate"]`. Missing or `off` is off; `on` is on (case-insensitive); anything else stops: `project.md's Require teammate approval is <value>; use on or off`.

### Reads

`FIELDS` gains `author,reviews,reviewDecision,reviewRequests`. These are gh reads only; nothing is written.

### Gate: GitHub's required reviews (always)

Right before the mergeability check, whatever the row says: when `reviewDecision` is `REVIEW_REQUIRED`, stop with

`required reviews missing: waiting on <names>`

where `<names>` lists `reviewRequests` in GitHub's order, comma-separated: a user as their login, a team as `@<org>/<slug>`. When `reviewRequests` is empty (a ruleset that names no one), it reads `waiting on required reviewers`.

A blank or missing `reviewDecision` (no required reviews) changes nothing, so a repo without protection merges as today.

### Gate: teammate approval (row `on`)

Runs right after the required-reviews check, also before the mergeability check, so it names the cause first.

1. Take the PR's reviews whose author is not the PR author (logins compared case-insensitively). The author's own reviews never count.
2. Keep verdict reviews only: `APPROVED`, `CHANGES_REQUESTED`, `DISMISSED`. Drop `COMMENTED` and `PENDING`.
3. For each reviewer keep their latest verdict review by `submittedAt`.
4. If any reviewer's latest is `CHANGES_REQUESTED`, stop: `changes requested by <logins> on PR #N`.
5. Pass if some reviewer's latest is `APPROVED` and its `commit.oid` equals `headRefOid`.
6. Otherwise stop with the first that fits:
   - a latest `APPROVED` on another commit: `no approving review on head <head short>; approved <old short>, head moved`
   - other reviewers' latest verdicts exist: `no approving review by a user other than <author> on head <head short>; latest reviews are <login STATE, ...>`
   - none at all: `no approving review by a user other than <author> on head <head short>`, plus `; the author's own approval does not count` when the author has an `APPROVED` review (GitHub refuses those, but the API data can still carry one from an imported or edited review).

All of these are exit 1, a stop, like every other gate line.

### `MERGE READY` and the merge block

- `ship-loop` § Team mode `MERGE READY` gets `Reviews needed: <requested reviewers, or "none">` after `Security review PASS:`. The builder reads it from `./scripts/gh.sh pr view <N> --json reviewRequests`, formatted like the gate's names. It informs the user only; the gate re-reads GitHub at merge.
- `chief-of-staff/approvals.md` merge block gets `GitHub reviews: <the child's Reviews needed line>` under `Reviews:`, so the user sees it before replying `approve N`.

### Docs

- `merge-pr` SKILL checks list: add the required-reviews check and the teammate rule when the row is `on`.
- `docs/agents/github-auth.md` § Merge gate: replace "the gate needs no branch protection, ruleset or CODEOWNERS file" paragraph with: the gate still needs none of them; if they require a review, the gate waits on GitHub's required reviewers by name; `Require teammate approval` adds the teammate rule on top of the user's `approve N`.

### Tests

In `agent-team/scripts/test_merge_pr.py`, `green()` gains `author`, `reviews: []`, `reviewDecision: ""`, `reviewRequests: []`, `teammate: None`.

- One table-driven test for the teammate rule (row `on`): no reviews; author-only approval; approval on an old head; approval then a later changes-requested from the same reviewer; a commented review after an approval (still passes); approval on the current head (passes); the row `off` with no reviews (passes); a bad row value.
- One table-driven test for required reviews: `REVIEW_REQUIRED` with a user and a team names both; with no requests says `required reviewers`; `APPROVED` and `""` pass.

## How this sits on top of #132 (CW-125)

#132 also edits `merge_pr.py` (the base check right above where these checks go, and the root-branch lines), `test_merge_pr.py` (a new test after `test_gate`), `templates/project.md` (a `Merge target branch` row after `Branch pattern`), and the skill and doc files above.

This branch starts from `origin/main` and stays out of #132's lines where it can: the new row goes after `Owner login`, the new gate checks sit after the head check and say nothing about branch names, and the new tests go at the end of the test file. If #132 merges first, this branch merges `origin/main` in before `MERGE READY`, keeps both sides of any conflict, runs the full test suite, and gets both reviews on the merged head. If this one merges first, #132 does the same.

## Calls I made

- A standing `CHANGES_REQUESTED` from any teammate stops the merge, even when another teammate approved the head. The ticket only said what counts as an approval; this matches how GitHub treats required reviews and keeps a "please don't merge" from being outvoted by a second reviewer.
- A row value other than `on` or `off` stops the merge rather than counting as `off`, so a typo can't switch the rule off.
- The teammate check runs before the mergeability check (next to the required-reviews check), so a repo with protection gets the teammate line, not `state BLOCKED`.
- `cos_approve_pr.py` (including `--auto`) does not check reviews. `merge_pr.py` re-reads them at merge, which is the gate that counts; adding the check to both would mean two copies of the rule.
- `CHANGES_REQUESTED` as a `reviewDecision` gets no new line of its own; with the row `off` it falls through to the mergeability check as today.
- The `Reviews needed:` line shows only pending review requests, not whether a teammate already approved.
- This repo's own `docs/agents/project.md` doesn't get the row (so it stays `off`); the ticket only asks for the template.
- Teams print as `@<org>/<slug>`, built from the `reviewRequests` entry's organization and slug fields; the plan checks the exact gh shape for a team request.

## Out of scope

- Holding the ticket while it waits for the teammate (#128).
- Who may send `approve N`.
- Submitting, dismissing or requesting reviews from any agent or script.

## Proof plan

- The two table-driven tests above, plus the full suite.
- A live read: `merge_pr.py`'s fact read against an open PR prints the new fields' shape (empty reviews today).
- Not provable here: a real teammate approval, since the repo has one human account.
