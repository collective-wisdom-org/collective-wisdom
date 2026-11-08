# CW-199: Run the docs check once, after the code and security reviews pass

**Status:** Shipped
**Shipped:** in PR #202, as specified
**Ticket:** [#199](https://github.com/collective-wisdom-org/collective-wisdom/issues/199)
**Related:** CW-197 (#197, open) compacts the same skills. Whichever merges second rebases its text edits.

## Goal

The documenter runs once per PR, after the code review and security review both pass. A docs fix commit after that does not start another docs check, and starts the reviews again only when it touches a file that changes behavior.

## Today

Facts from `main` at `19f815d`.

- `open-pr` § Docs check runs the documenter right after the closeout commit (step 1), commits fixes (step 2), keeps the check "current" through later fix commits and same-diff target merges (step 3), and runs it again before a later code review pass when it is not current (step 4). Every `CHANGES NEEDED` fix commit makes it stale.
- `open-pr` § Agent review comment loop puts the `DOCS CHECK` result in the code review brief, adds `Docs checked: <files> at <short SHA>` to the `## Code review` comment, and makes a missed rerun a **Must fix**. `docs/agents/code-review.md` § Method step 3 says the same. `ship-loop` copies `Docs checked` into `MERGE READY` from the latest code review comment.
- `merge_pr.review` accepts a PASS older than the head only through `merge_pr.stands`: the latest `Head moved to ...` note by the gh user must name the head and the reviewed head, match `NOTE` (`Head moved to <sha> ... unchanged since <sha>`) or the conflict note, and `pr_diff_delta.delta` must say `same`. `review_gate.verdict` builds the same note when the delta is `same` and prints `rerun` for anything else. Both call `merge_pr.review`, so they agree.
- `pr_diff_delta.delta(reviewed, head)` compares the PR's diff (each head against its own merge base with `origin/<target>`) per file by modes and blob IDs, and returns `("same", [])` or `("changed", files)`.
- `review_scope.is_docs(path, modes)` is the docs-file rule: an ASCII `.md` file that is top-level `README.md` or under `docs/` but not `docs/agents/`, with no hidden path part, not named `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md`, and a regular file on both sides. `review_scope` imports `pr_diff_delta`.

## Builds

### 1. The docs check moves to the end

New order in a run with agent reviews:

1. Open the PR, commit closeout docs.
2. Code review loop to PASS, then security review to PASS (or the docs-only skip, or the combined `small` pass; § Review scope is unchanged).
3. **Docs check, once**, on `origin/<target>...HEAD` at the head both reviews passed on. Same documenter subagent, same inputs, same "documenter changed nothing" check. Apply the right findings in one `docs: bring docs in line with <PREFIX>-N` commit and push.
4. Post a PR comment, as the builder:

   ```
   ## Docs check

   <the DOCS CHECK line>
   Docs checked: <files the fix commit changed, or "nothing stale"> at <checked short SHA>
   Rejected: <finding and why, one per line, or "none">
   ```

5. `wait-for-ci.sh`, then `review_gate.py`, acting on its last line as today. `note` now also covers a head moved by docs-file changes (§ 2). `rerun` runs both reviews again until PASS; the docs check does not run again.

"Once" is checked from the PR, not from memory: run the docs check only when the PR has no `## Docs check` comment by the gh user. The one exception is `Review after conflict resolution` `on`: after both reviews pass on a resolved head, run it once more when no `## Docs check` comment is newer than the resolved head commit. With `off` the resolution runs no docs check, as today.

A teammate's requested changes (`ship-loop` § Changes requested) send the run back to build and through both reviews; the docs check does not rerun.

### 2. Reviews stand through docs-file changes

`pr_diff_delta.delta` gets a third kind: `("docs", files)` when at least one file differs and every differing file passes the docs-file rule on its modes at both heads (a file absent at one head counts as mode `000000`, as `review_scope` treats it). Anything else that differs stays `("changed", files)`. The CLI prints `pr-diff-delta: docs since <reviewed> at <head>: <files>` for it, exit 0.

`is_docs` and its constants move from `review_scope.py` to `pr_diff_delta.py`, and `review_scope.py` uses them from there (it already imports `pr_diff_delta`, so the reverse import would loop). The rule itself does not change.

`merge_pr.stands` accepts a delta of `same` or `docs`. Its `NOTE` regex also matches the new note wording below. Every other condition stays: the note is the latest `Head moved to` note by the gh user, names the current head and the reviewed head, the review was posted on the reviewed head, and the delta is recomputed at merge.

`review_gate.verdict`, when the delta is `docs`, prints this note and `review-gate: note head <head> reviewed <reviewed>`:

```
Head moved to <head>; PR diff changed only in docs files since <reviewed>: <files>. Reviews from <reviewed> stand.
```

`same` keeps today's merge note. `changed` keeps `rerun`. Run again after posting the note, both scripts print `pass` through the same `merge_pr.review` call.

Under this rule a docs fix in a skill, role doc, `AGENTS.md`, `CLAUDE.md` or `docs/agents/project.md` is not a docs file, so the reviews run again on it, once. A fix only in `README.md` or `docs/superpowers/` (the spec, as-built, release notes) stands.

### 3. Why it ends

| After both PASS at H, the docs check finds | Then | Docs checks | Review rounds after the check |
|---|---|---|---|
| nothing stale | `review_gate` `pass` at H | 1 | 0 |
| fixes only in docs files | fix commit F, `note`, `pass` at F | 1 | 0 |
| a fix in a skill or role doc | F, `rerun both`, reviews run until PASS at F or a later fix head, `pass` | 1 | 1 or more, ended by the review loop as today |

The docs check runs only in step 3, which the `## Docs check` comment closes, so a review round after it can never start another. The only loop left is the review loop itself, which today's PASS bar ends.

### 4. CI review mode

The docs check runs after the `ci` mode loop is done: `wait-for-ci.sh` is `pass` on the head and `ci_review.py list <N>` exits 0. A fix commit goes back to `open-pr` § CI review mode step 2: wait for CI, run `list`, and handle any bot thread on the fix like any other. The docs check does not rerun. `review_gate.py` prints `ci` in this mode, so § 2 does not apply. `MERGE READY`'s `Docs checked` comes from the `## Docs check` comment.

### 5. Text that names the old order

- `open-pr` § Docs check: rewritten as § 1 (when, inputs, the comment, the once rule, the conflict `on` exception). Steps 3 and 4 go.
- `open-pr` § Closeout docs: the "re-run below backs this up" sentence becomes "the docs check after both reviews pass reads them once".
- `open-pr` § Agent review comment loop: the brief no longer carries a docs result; the `Docs checked:` line leaves the `## Code review` shape; the **Must fix** sentence about a missed rerun goes.
- `open-pr` § Done when: drops "the docs check is current".
- `open-pr` § Conflict resolution step 4 `on`: both reviews, then the docs check once (§ 1). § CI review mode step 1 drops the docs check; a new last step runs it (§ 4).
- `ship-loop` § Phase gates: "docs check current" leaves PR opened → Security-ready; Security-ready → Merge-ready adds "the docs check ran once after both PASSes (a `## Docs check` comment)". § Phases 3 drops the docs check; § Phases 4 runs it after the security PASS and before `review_gate.py`. `Docs checked` in `MERGE READY` comes from the latest `## Docs check` comment, in both modes.
- `docs/agents/code-review.md` § Method step 3 goes, and the line naming the `Docs checked:` line in the comment.
- `docs/agents/org-chart.md`: the stage label lists the docs check after the reviews, and the Documenter row says when it runs.
- `.claude/agents/documenter.md` description: "after the code and security reviews pass". `code-reviewer.md` description: drops "after the docs check".
- Script headers: `pr_diff_delta.py` (the `docs` line), `review_gate.py` (the `note` cases), `merge_pr.py` (what a reviews-stand note covers).

### 6. Tests

- One table-driven test that builds a real git fixture (a base, a PR head H with both PASSes, then one fix commit F) and runs `review_gate.verdict` and `merge_pr.review` on the same facts with the real delta. Rows: F touches only `docs/superpowers/specs/x.md` gives `note`, then `pass` once the note is posted; F touches `agent-team/.claude/skills/x/SKILL.md`, `docs/agents/x.md` or `a.py` gives `rerun both`, and `merge_pr.review` reports a problem for both reviews. Each row asserts the two scripts agree.
- The existing `test_pr_diff_delta.py` table gains a `docs` row and a mixed docs-plus-code row that stays `changed`.

## Leaves out

- The documenter checklist (`docs/agents/documenter.md`) and what counts as stale.
- `review_scope.py` classes, the docs-file rule and the 200-line limit.
- Skipping the docs check on small diffs.
- Enforcing the docs check in a script. Neither `review_gate.py` nor `merge_pr.py` reads the `## Docs check` comment.

## Calls I made

- **A later docs-file-only commit of any kind stands, not just the docs check's fix.** The rule reads the files, as the ticket asks, so a `**Shipped:**` line or as-built tweak after the PASSes also keeps the reviews. Code review of those files is skipped; security review of docs-only diffs is already skipped today.
- **The docs-file rule is `review_scope.is_docs` as is, not a wider list.** Skills, role docs and `project.md` drive agents and scripts, so a docs fix there gets one more review round. In this repo that will be the common case when the documenter finds something. I judged one review round on a real behavior change cheaper than a second rule to keep in step.
- **Code fixes after the docs check are not re-checked.** If a review round after the docs check changes what ships, the builder keeps the `**Shipped:**` line, as-built, release note and `## Proof` current in the same commit (`open-pr` § Closeout docs, as today). The documenter does not see it.
- **A `## Docs check` PR comment records the check.** It is how a later session (a Sonnet switch or a continuation task) knows the check ran, and it is the source of `MERGE READY`'s `Docs checked` line now that the code review comment no longer has one.
- **One note regex, two wordings.** `stands` accepts `same` or `docs` from the recomputed delta under either note, so the note text informs and the files decide.
- **`is_docs` moves into `pr_diff_delta.py`** so `pr_diff_delta` can use it without a circular import. No behavior change for `review_scope.py`.

Touches: none of these (no data, money, auth, user email or migrations).
