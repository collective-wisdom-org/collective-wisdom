---
name: open-pr
description: >-
  Opens a review-ready GitHub PR, then autopilot and code review loop
  to PASS (phase 3). Use when the user says make a pr, open pr, handle review,
  autopilot on PR N, fix CI, or gives a PR URL/number.
user-invocable: true
---

# Open PR and feedback loop

Read **ship-loop** § Repo invariants first; `<owner>/<repo>` is in `docs/agents/project.md` § Git and GitHub. Work and edit only from the feature branch in the PR's worktree when one exists.

## When to skip open

An existing PR (number or URL): start at **Feedback loop**. No PR yet: **Open**, then **Feedback loop**, in the same session.

## Open

### Verify

Run the plan's Task 0 verification or **build-from-plan** § Testing's scoped tests; fix failures before pushing.

### Proof

Every PR carries a `## Proof` section, written after § Verify and before `gh pr create`: evidence per Acceptance item (its Scope bullets when there is no Acceptance list) a reviewer can check in a minute or two, and a `Not proven` list. `~/.collective-wisdom/scripts/merge_pr.py` refuses a PR without the section or a line starting `Not proven`.

````markdown
## Proof

- **<Acceptance item, short>**: <what shows it holds>

  ```
  $ <command>
  <trimmed output: the lines that show the result>
  ```

- **<next item>**: CI run <link>, job `<name>` passed at <short SHA>.

Not proven:
- <item or check>: <why: blocked, no browser, needs a deploy, ...>
````

`Not proven: nothing` when every item has proof.

- Evidence is real output from this branch, never hand-written: a command with trimmed output, a CI run link, a screenshot on GitHub (never an image file in the branch), or a note of what was done and seen (a prose change: the lines that make the item hold).
- Under `Not proven` with the reason: items with no evidence, skipped CI jobs, tests marked skip, manual plan checks that couldn't run, a visual check with no way to attach a screenshot.
- A fix commit that changes what an entry shows updates it in the same push (`~/.collective-wisdom/scripts/gh.sh pr edit <N> --body-file <path>`).

### Superpowers docs

Follow **superpowers-project-memory** § PR checklist, except: before `gh pr create` only the spec (retroactive if needed) and its plan must exist (no plan for a markdown-only ticket); no index rows; the **Shipped** line and any as-built come right after the PR exists (§ Closeout docs).

### Create PR

Follow the **creating-pr** skill end to end, with these overlays:

- Its `gh` calls are `~/.collective-wisdom/scripts/gh.sh`; pushes use the user's own gh auth.
- PR body: link **<PREFIX>-N** (`ticket-url`) and the spec path; add `## Release note` when notes are on (§ Closeout docs), `## Proof`, and `Context size: <before> to <after> characters (<net> from <target>)` from the compaction totals (`Context size: pass skipped (<reason>)` when it skipped); the as-built path only when one exists. With the `Tracker` row `github`, add `Closes #N` (for another merge target branch, `merge-pr`'s `set-state` Done closes it).
- `set-state` the linked ticket to **In Review** when the tracker is available. Wait for CI per `ship-loop` § CI waits.

### Closeout docs

Right after the PR exists, before the first code review pass, edit the linked spec:

- Build matches: set `**Status:** Shipped` and add `**Shipped:** in PR #N, as specified` (no date).
- Build differs: write an as-built (`reference.md` § As-built template) and link it: `**Shipped:** in PR #N, with differences: [as-built](../as-built/<file>.md)`. It differs when a reader of the spec would be wrong about what shipped: a behavior, flag, exit code, file or rule the spec states differently or not at all (not a refactor of code layout).

Unless `Publish release notes` in project.md § Docs is `off`, add a `## Release note` to the PR body (`~/.collective-wisdom/scripts/gh.sh pr edit <N> --body-file <path>`): one to three sentences for a user of the agent team on what they will notice and need to do, if anything; no file lists or implementation detail.

Commit the spec (and as-built) on the feature branch as `docs: shipped line for <PREFIX>-N <short>` and push before step 1 of the agent review loop. A later fix commit (phase 3 or 4) that changes what ships updates the `**Shipped:**` line or as-built, the release note and `## Proof` in the same commit. Then go to **Feedback loop**; never merge or approve (§ Forbidden).

### Docs check

Run once per PR, after both reviews PASS (or the docs-only skip, or the combined `small` pass), and only when the PR has no `## Docs check` comment by the gh user (`~/.collective-wisdom/scripts/gh.sh pr view <N> --comments`); again after a conflict resolution with `Review after conflict resolution` `on`, once both reviews pass on the resolved head, when no `## Docs check` comment is newer than that head commit. Steps and comment: `reference.md` § Docs check. In `ci` mode see § CI review mode.

## Feedback loop

With `Review mode` `ci`, skip § Review scope and § Agent review comment loop and follow § CI review mode.

### Primary loop

If the **autopilot** skill is available (Cursor), follow it in full, with `gh` as `~/.collective-wisdom/scripts/gh.sh` and every CI wait per `ship-loop` § CI waits. Otherwise (Claude Code) loop until checks are green and every review comment is answered, or you are blocked:

1. `~/.collective-wisdom/scripts/gh.sh pr view <N> --json mergeable,mergeStateStatus,headRefName`. If the branch conflicts with the merge target branch, merge `origin/<target>` into it in the worktree, resolve what has one clear answer and push; for the rest stop with `BLOCKED: <question>`. A conflict found after `MERGE READY` follows § Conflict resolution.
2. Wait for CI (`ship-loop` § CI waits). On `conflict with <target>`, go back to step 1. For each failing check, read `~/.collective-wisdom/scripts/gh.sh run view <run-id> --log-failed`, fix the cause, run the matching local check, commit and push.
3. Read new review comments (`~/.collective-wisdom/scripts/gh.sh api repos/<owner>/<repo>/pulls/<N>/comments` and `~/.collective-wisdom/scripts/gh.sh pr view <N> --comments`). Fix what is clearly right and reply in thread (§ Inline review replies); reply with the reason when a suggestion is wrong; a comment that needs a product decision is `BLOCKED: <question>`.
4. After every push, start again at step 1.

Act only on review comments from the login `user.md` maps to this repo, one of the four team logins (Chief of Staff, builder, code reviewer, security reviewer) in `docs/agents/project.md`, or a repo review bot. Report others in your final message, don't act on them.

### Conflict resolution

`reference.md` § Conflict resolution: the relay `the PR conflicts with <target>` after `MERGE READY` starts it. Before the first `MERGE READY` the relay is Primary loop step 1 (post no `reviews stand` note).

### Review scope

Before each review pass, run `~/.collective-wisdom/scripts/review_scope.py <N> <head SHA> --next` with the full SHA of the head you review, and do what its `next:` line says. Each pass uses the class of its own head (a fix can grow a `small` PR into `full`).

### Agent review comment loop

After each primary loop pass, when doing agent-led review:

- The review method is `~/.collective-wisdom/docs/agents/code-review.md`; the worktree checkout must be the PR head branch.
- Run it in a subagent so it stays on the review model: `subagent_type: "code-reviewer"` (fallback: `ship-loop` § Models). The brief includes the ticket's Acceptance list (its Scope bullets when there is none) and the PR body's `## Proof`.
- Post findings as a **PR issue comment** only: `~/.collective-wisdom/scripts/gh.sh pr comment <N> --body '…'` or `--body-file <path>`. Post each code review comment before you mention it in the thread, and keep its URL.

**Comment shape:** title line `## Code review (pass N)`; end with **Verdict:** `CHANGES NEEDED` or `PASS`.

**Loop until pass:** review and post the comment (pass N). On **CHANGES NEEDED**, fix all **Must fix** items, commit and push (closeout docs per § Closeout docs, same commit), wait for CI (`ship-loop` § CI waits), re-review (focus on code changed since the last pass) and post the next pass, until the latest agent verdict is **PASS**.

If the code is good, post **PASS** on pass 1; don't invent issues. Missing tests are a **Must fix** only for the areas in `AGENTS.md` § Testing. Flag excess tests too: one-test-per-edge-case that should be a table, tests for styling or small UI interactions, tests that pin constants.

### Inline review replies

Reply **in thread**, not top-level, starting the body with `Fixed in {short-sha}.`: `~/.collective-wisdom/scripts/gh.sh api -X POST repos/<owner>/<repo>/pulls/<pr>/comments/<comment_id>/replies -f body='Fixed in abc1234. …'`

### Forbidden (feedback loop)

- Any GitHub review: `gh.sh pr review`, approve, request changes (`ship-loop` § Repo invariants)
- Merging: **merge-pr**'s job (`merge_pr.py`), only on a merge approval (`ship-loop` § Approvals)
- Enabling auto-merge or marking a draft ready without the user's ask

### Optional

Bugbot, when asked (Cursor only): read the **review-bugbot** skill and fold its findings into your PR comment.

### Done when

Checks green, review comments answered, closeout (spec **Shipped** line, any as-built, release note) in the PR and, when agent review ran, the latest **code review** verdict **PASS**. Report **code review complete** and go to **security-review** (phase 4) in the same session; never report merge-ready here. Repeat **Feedback loop** until code review **PASS** or blocked.

## CI review mode

`reference.md` § CI review mode (`Review mode` `ci`): the review bot replaces § Review scope and § Agent review comment loop.

## When to read reference.md

`reference.md` § Conflict resolution (relay `the PR conflicts with <target>` after `MERGE READY`); § CI review mode (`ci` mode); § Docs check (running it); § As-built template (a build that differs from its spec).
