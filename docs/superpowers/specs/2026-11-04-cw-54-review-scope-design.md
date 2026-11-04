# CW-54: Skip the security review on docs-only diffs and merge the two review passes for small ones

**Ticket:** [CW-54](https://github.com/dbeallor/collective-wisdom/issues/54)
**Status:** Shipped
**Shipped:** in PR #93, as specified

## Goal

Spend fewer Opus reviews where they find nothing. A PR that only changes docs gets a real code review and a security review comment that says it was skipped. A small PR gets both reviews from one subagent run. Everything else is reviewed as today.

**Security review: look at this on purpose.** This weakens the phase 4 gate for two kinds of PR. § Security notes says what that trades.

## Today

Facts from `main` at `57e7470`, checked 2026-11-04.

- `open-pr` § Agent review comment loop runs the `code-reviewer` subagent (Opus) and posts `## Code review (pass N)`. `security-review` § Primary review path and § PR comment loop run the `security-reviewer` subagent (Opus) and post `## Security review (pass N)`. Each loop re-reviews after every fix push.
- `ship-loop` § Team mode **Build stage** requires the latest `## Code review` and `## Security review` comments to end in PASS with no commit after them, except a head moved only by a `main` merge that `scripts/pr_diff_delta.py` calls `same`.
- `scripts/merge_pr.py` `review()` requires, for each heading, a latest comment by that role's login whose last line is `Verdict: PASS` and that is newer than the head commit (or stands under the `Head moved to ...` note). It does not read the comment's body otherwise.
- The rule "re-review after a `main` merge only when `pr_diff_delta.py` says `changed`" is written once, in `ship-loop` § Team mode **Build stage**. `merge-pr` § Team mode and `open-pr` § Docs check point to it. Nothing to dedupe.
- `pr_diff_delta.py` takes a PR's diff at a head against that head's merge base with `origin/main` (`raw_entries`). Its `run`, `fetch` and `CmdError` are reused by `merge_pr.py`.
- In this repo `docs/agents/` holds `project.md` (owner login, agent logins, security overlays) and links to the role docs. In an app it holds the installed role docs. Both are instructions agents follow, not records.

## Change

### 1. Classifier: `agent-team/scripts/review_scope.py`

```
scripts/review_scope.py <PR number> [<head SHA>]
```

- Fetches `main` and the PR head the way `pr_diff_delta.py` does (imports its `run`, `fetch` and `CmdError`; head defaults to `headRefOid` from `./scripts/gh.sh pr view`).
- Takes the diff at the head against its merge base with `origin/main`, with `--raw` and `--numstat`, `--no-renames`.
- A file is a **docs file** when all of these hold:
  - its path is ASCII and ends in `.md`;
  - it is `README.md` at the repo top, or under `docs/` but not under `docs/agents/` (compared without regard to case, so `docs/Agents/` and lookalikes such as `docs/agentſ/` stay out on a case-insensitive checkout);
  - it is a regular file on both sides (mode `100644`, or absent on one side). A symlink or executable never counts.
- **Changed lines** are added plus deleted lines from `--numstat`, over the files that are not docs files. A binary file (`-` in `--numstat`) makes the PR `full`.
- Class, checked in this order:
  - `docs-only`: at least one file changed, and every changed file is a docs file. An empty diff is `small`.
  - `small`: changed lines are 200 or fewer.
  - `full`: anything else.
- Exit 0, last line (full SHA):
  - `review-scope: docs-only at <head>: <N> files`
  - `review-scope: small at <head>: <L> lines in <M> files`
  - `review-scope: full at <head>: <L> lines in <M> files` (or `: binary <file>`)
- Exit 2: bad arguments or a read failed. Last line `review-scope: cannot <what>`. Exit 2 means review as `full`.

Tests: one table-driven test in `scripts/test_review_scope.py` over a temp git repo, in the style of `test_pr_diff_delta.py`: docs only under `docs/superpowers/` (docs-only), a root `README.md` (docs-only), a `docs/agents/*.md` change (not docs-only), a symlinked `.md` under `docs/` (not docs-only), a `.md` outside `docs/` such as a skill (small), docs plus 200 lines of script (small, docs lines not counted), 201 lines (full), a binary file (full), a bad SHA (exit 2).

`scripts/test_symlinked_root.py` adds `review_scope.py` to the scripts allowed to exit 2 on `--help`, as `pr_diff_delta.py` is.

### 2. Where it runs

A new `open-pr` § Review scope, right before § Agent review comment loop:

1. Before each review pass (code review pass 1, and every re-review), run `./scripts/review_scope.py <N> <head SHA>` with the full SHA of the head under review. Only its last line decides the class. Any non-zero exit: run it again. Fail twice: review as `full`.
2. Each pass uses the class of the head it reviews. A fix that grows a small PR past 200 lines makes the next pass `full`.

By class:

- **`full`**: as today. Phase 3 code review loop, then phase 4 security review loop.
- **`docs-only`**: the code review runs as today. After its PASS, run `./scripts/review_scope.py <N> <head SHA>` again; only if it still prints `docs-only` at the head the code review passed on, phase 4 posts, with `AGENT_GH_ROLE=security-reviewer`, a comment with no subagent run:

  ```
  ## Security review (pass N)

  Skipped: docs-only diff. <the review-scope line>

  Verdict: PASS
  ```

  Post it after the code review PASS, on the same head, so no commit follows it.
- **`small`**: one `code-reviewer` subagent (Opus) reviews the diff once with both briefs: the code review brief from § Agent review comment loop, and the security list from `security-review` § Primary review path (**Custom Instructions**). It returns two sections, `CODE REVIEW` and `SECURITY REVIEW`, each with its own findings and verdict. The child posts both comments from that one run: `## Code review (pass N)` as `code-reviewer` and `## Security review (pass M)` as `security-reviewer`, each in its usual shape. When either verdict is `CHANGES NEEDED`, fix, push, wait for CI and run the next combined pass, which posts both comments again. Phases 3 and 4 end together when both latest verdicts are PASS on the same head.

### 3. Docs

- `docs/agents/code-review.md`: a short § Small diffs: when the brief says `small`, also review against the security list in the brief and return `CODE REVIEW` and `SECURITY REVIEW` sections, each with findings and a verdict.
- `security-review` SKILL: one line at the top of § Primary review path pointing to `open-pr` § Review scope for `docs-only` (skip comment) and `small` (already posted from the combined run).
- `ship-loop`: one sentence in phase 4 pointing to `open-pr` § Review scope. No edit to § Team mode, so the Build stage gate and the `MERGE READY` block stay as they are.
- `docs/agents/org-chart.md`: the Code review row adds "and, on a small diff, the security review in the same run"; the Security review row adds "skipped on a docs-only diff (`open-pr` § Review scope)". No chart change.

`merge_pr.py`, `cos_brief.py` and the Chief of Staff skills don't change: both headings still appear, by the same logins, ending in PASS.

## Security notes

- **What a docs-only skip trades.** Markdown under `docs/` (specs, plans, as-builts, release notes) and the top `README.md` are records that no script reads as instructions, so a security review of them has little to find. The cost is that a hostile line in a spec (a prompt injection aimed at a later agent) gets only the code review. The docs exclusion of `docs/agents/` keeps `project.md` (logins, overlays) and the role docs under a full review. Skills are under `.claude/`, so they never count as docs.
- **Trust in the class.** The child runs the classifier and writes the skip comment; `merge_pr.py` doesn't re-check that the diff was docs-only. That is the same trust it already places in the child posting a real review comment, and the owner still approves the head on GitHub. A check in `merge_pr.py` is out of scope (see Calls).
- **Small diffs still get a security review,** by the same Opus model against the same list, in a shared run. The risk is a reviewer giving less attention to security when it also reviews the code.
- **Symlinks and executables never count as docs,** so a `.md` link pointing into a skill can't pass as a doc.

## Acceptance

- A docs-only PR has one code review comment from a subagent run and a `## Security review (pass 1)` comment saying `Skipped: docs-only diff` ending in `Verdict: PASS`, and `merge_pr.py` accepts it.
- A small PR has a code review comment and a security review comment produced from one subagent run.
- A PR over 200 lines outside docs is reviewed as today.
- `test_review_scope.py` covers the rules in § 1.

## Non-goals

- Changing what either review checks.
- A check in `merge_pr.py` or `cos_brief.py` that the skip was allowed.
- Changing when reviews re-run after a `main` merge (`pr_diff_delta.py`).
- The install PR in apps. It follows the next tag.

## Calls I made

- **`docs/agents/` never counts as docs.** The ticket says "markdown under `docs/`". In this repo that folder holds `project.md` (owner and agent logins, security overlays), and in apps it holds the installed role docs, which agents follow. Both get a full security review.
- **The size measure ignores docs files.** A small script change with a 100-line spec and plan is `small`, not `full`. The spec and plan lines aren't counted.
- **The threshold is 200 changed lines** (added plus deleted, outside docs). PR #34 (326 lines) stays `full`. Easy to tune later; it's one constant.
- **`merge_pr.py` doesn't verify the skip.** The ticket says it needs no change, and the owner approves every head. Adding a re-check there would be cheap if wanted.
- **The class is taken per pass, on the head being reviewed,** so a fix that grows the diff moves it to `full`, and a later pass can't skip a review the earlier class needed.
- **The combined run uses the `code-reviewer` subagent** with both briefs, not a new agent file. No new role, and CW-72's org-chart edits don't clash with a new row.
- **The skip comment is posted only after code review PASS,** on that same head, so its position in phase 4 doesn't change.
- **A new script, not an extension of `pr_diff_delta.py`.** That script answers "same or changed between two heads"; this one classifies one head. It reuses the fetch and run code.
- **Only paths starting with `docs/` count, not `agent-team/docs/`.** In this repo the shared role docs sit under `agent-team/` and are reached through links, so their real paths never match. `docs/agents/` (including its `README.md` role index) is excluded by name.
- **Ship-loop and org-chart edits are one sentence each,** to keep the rebase onto CW-72 easy.
