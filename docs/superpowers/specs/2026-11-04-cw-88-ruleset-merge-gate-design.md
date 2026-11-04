# CW-88: Accept a repository ruleset as the merge gate protection

**Ticket:** [CW-88](https://github.com/dbeallor/collective-wisdom/issues/88)
**Status:** Draft

## Goal

`scripts/merge_pr.py` accepts a repository ruleset on `main` that requires an approving review, in place of (or alongside) classic branch protection. When it finds no protection, its message says whether it found none or could not read it.

## Today

Facts from `main` at `57e7470`, checked 2026-11-04.

- `read_protection` in `agent-team/scripts/merge_pr.py` calls `gh api repos/{owner}/{repo}/branches/main/protection` and returns `required_pull_request_reviews.required_approving_review_count` (0 when the key is missing). Any HTTP 404 returns `None`; any other error raises, and `main` turns that into exit 2 (`merge-pr: cannot read PR #N: ...`).
- `gate` stops with `main has no branch protection requiring an approving review; set it up per docs/agents/github-auth.md § Merge gate` when `f["protection"]` is falsy (`None` or 0).
- `merge_pr.py` runs as the owner (it drops `AGENT_GH_ROLE` and refuses an agent login). Checked live:
  - Owner, `main` (classic protection set): `200`, count `1`.
  - Owner, a branch with no protection: `404` with message `Branch not protected`.
  - Builder (no admin), `main`: `404` with message `Not Found`.
- So the 404 message tells the two cases apart: `Branch not protected` means readable and absent; `Not Found` means the caller can't read it.
- `GET repos/{owner}/{repo}/rules/branches/main` returns the active rules that apply to `main`, from repo and org rulesets, as a JSON array. Owner and builder both get `200 []` today (the repo has no rulesets now; `GET repos/{owner}/{repo}/rulesets` is `[]`). A `pull_request` rule looks like `{"type": "pull_request", "parameters": {"required_approving_review_count": 1, ...}, "ruleset_id": ...}`. Rulesets in `evaluate` mode are not active and don't appear.
- `docs/agents/github-auth.md` § Merge gate describes only classic protection and its verify command.
- `merge-pr` SKILL (checks list, Team mode) and `org-chart.md` say "branch protection on `main`".
- Tests: `test_merge_pr.py` fakes the classic endpoint from `f["protection"]` (an int, or `None` for a `Branch not protected` 404) and has two gate rows for it.

## Change

### `read_protection(run)`

Reads both sources and returns `(count, unread)`:

- `count`: the largest `required_approving_review_count` found across classic protection and every `pull_request` rule, or 0 when neither has one.
- `unread`: the sources it could not read, as short strings for the message (`branch protection: Not Found`, `rulesets: Not Found`).

Per source:

| Source | Result | Counts as |
|---|---|---|
| Classic `branches/main/protection` | 200 | its count (0 if no PR reviews) |
| Classic | 404 `Branch not protected` | none, read fine |
| Classic | any other 404, or 403 | unread |
| Rules `rules/branches/main?per_page=100` | 200 | largest count among `pull_request` rules, 0 if none |
| Rules | 404 or 403 | unread |
| Either | any other error | raises, as today (exit 2) |

`read_facts` stores the pair in `f["protection"]` (still `None` when the PR isn't open).

### `gate`

Replaces the one protection check with:

- `count >= 1`: pass, go on to `owner_approval`.
- `count == 0` and `unread` is empty: `main has no branch protection or ruleset requiring an approving review; set it up per docs/agents/github-auth.md § Merge gate`.
- `count == 0` and `unread` is not empty: `cannot read main's protection (<unread, joined with "; ">) and found none requiring an approving review; check per docs/agents/github-auth.md § Merge gate`.

Both are exit 1 (a stop), like today. The first message still starts with `main has no branch protection`, so the `merge-pr` skill's quote stays true.

### Docs

- `agent-team/docs/agents/github-auth.md` § Merge gate: step 2 offers two setups, a classic branch protection rule (as today) or a repository ruleset targeting `main` with the same settings: require a pull request, 1 approval, dismiss stale approvals on push, require code owner review, required status checks, enforcement `Active`, no bypass list. Step 3 lists both verify commands and what they print:

  ```bash
  ./scripts/gh.sh api repos/<owner>/<repo>/branches/main/protection --jq .required_pull_request_reviews.required_approving_review_count
  # classic: prints 1

  ./scripts/gh.sh api repos/<owner>/<repo>/rules/branches/main --jq '[.[] | select(.type == "pull_request") | .parameters.required_approving_review_count] | max'
  # ruleset: prints 1 (null when no ruleset requires a review)
  ```

  Then the two stop messages and what each means. The intro paragraph's "branch protection on `main`" becomes "branch protection or a ruleset on `main`".
- `merge-pr` SKILL: the checks list says "branch protection or a ruleset on `main` requiring an approving review"; Team mode adds the `cannot read main's protection ...` stop to the ones that end in `BLOCKED: <the script's last line>`.
- `org-chart.md`: same wording swap in the one sentence that mentions it.

### Tests

In `agent-team/scripts/test_merge_pr.py`:

- One table-driven test of `read_protection` with a fake runner that serves each source as a 200 body or an error. Rows: classic only, ruleset only, both (larger count wins), neither (both read fine), ruleset array with no `pull_request` rule, classic `Not Found` with a ruleset (passes), classic `Not Found` and nothing else (unread), and a 500 (raises).
- The existing gate rows change to the new shape: `(0, [])` → "no branch protection or ruleset", `(0, ["branch protection: Not Found"])` → "cannot read main's protection". `green()` uses `(1, [])`.
- The `fake` runner in the `main` tests also answers the rules endpoint (`[]`), so `test_main_writes` keeps working.

## Calls I made

- **The 404 message decides "none" vs "cannot read".** Only a classic 404 whose message is `Branch not protected` counts as "read, and there is none". Any other 404, and any 403, is "cannot read". This rests on what GitHub returned in the live checks above; if GitHub changes the wording, the gate gets stricter (says "cannot read"), not looser.
- **A source that can't be read doesn't block a pass.** If one source shows a required review, the gate passes even when the other can't be read, as the ticket asks.
- **Other errors still abort.** A 5xx or network error on either endpoint raises and the script exits 2, as a classic read failure does today. Only 403 and 404 are turned into "unread".
- **One page of rules.** The rules request asks for `per_page=100` and reads one page. A branch with more than 100 active rules is not a case this repo or its apps have.
- **Org rulesets count.** The rules endpoint includes rules from org rulesets that target the repo. They count the same as repo rulesets; the ticket doesn't separate them and the gate's purpose is the same.
- **A 0-approval rule is no protection,** as today for classic.
- **I also update `merge-pr` SKILL and `org-chart.md`.** The ticket names only `github-auth.md`, but those two state the old check in the same words and the docs check would flag them.
- **No live ruleset check.** The repo has no ruleset right now, and changing GitHub settings is out of scope, so the ruleset path is covered by tests only.

## Out of scope

- Checking a ruleset's code owner review, stale-approval or bypass settings. The gate keeps requiring the owner's approving review on the head (`owner_approval`).
- Changing any GitHub setting.
- `cos_approve_pr.py` (it doesn't read protection).
