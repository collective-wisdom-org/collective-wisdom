---
name: open-pr
description: >-
  Opens a review-ready GitHub PR, then autopilot and code review loop
  to PASS (phase 3). Use when the user says make a pr, open pr, handle review,
  autopilot on PR N, fix CI, or gives a PR URL/number.
user-invocable: true
---

# Open PR and feedback loop

Before acting, read **ship-loop** § Repo invariants. `<owner>/<repo>` below is the repo in `docs/agents/project.md` § Git and GitHub.

Work from the feature branch in the PR's worktree (`.worktrees/<name>/` or T3 Code's under `~/.t3/worktrees/`) when one exists.

## When to skip open

If the user gave a **PR number or URL** and the PR **already exists**, skip **Open** below and start at **Feedback loop**.

If there is no PR yet (or the user said *make a pr* / *open pr*), run **Open** first, then **Feedback loop** in the same session — no separate handoff.

## Open

### Verify

- Run verification from the plan (Task 0) or scoped tests from **build-from-plan** § Testing.
- Fix failures before pushing.

### Superpowers docs

Read and follow **superpowers-project-memory** § PR checklist, with one override: before `gh pr create`, only the spec (retroactive if needed) and its plan must exist. The plan may be absent for a ticket that changes only markdown files (`ship-loop` § Team mode, Build stage). There are no index rows to write. The spec's **Shipped** line and any as-built come right after the PR exists, per § Closeout docs below.

### Create PR

Read and follow the **creating-pr** skill end-to-end (prepare branch, title, description, self-review, push, create PR).

**Overlays on creating-pr:**

- Use `./scripts/gh.sh` instead of bare `gh` (creating-pr already shows `./scripts/gh.sh pr create`).
- PR body: link **<PREFIX>-N** (`ticket-url`) and the spec path, add a `## Release note` section (see § Closeout docs), and add the as-built path only when one exists. When the `Tracker` row is `github`, also put `Closes #N` in the body so the merge closes the issue.
- Pushes use the user's own gh auth.
- **Tracker:** `set-state` the linked ticket to **In Review** when the tracker is available. Tracker operations are in `docs/agents/trackers/README.md`; the adapter is the one for the `Tracker` row in `docs/agents/project.md`.
- **CI:** `./scripts/gh.sh pr checks --watch`, or a PR/CI subscription when the agent has one.

### Closeout docs

Right after the PR exists (PR number known), before the first code review pass:

Closeout is a line in the spec and a section in the PR body. Edit the linked spec:

- Set `**Status:** Shipped`.
- Add `**Shipped:** in PR #N, as specified` (no date) when the build matches the spec.
- When the build differs, write an as-built and link it instead: `**Shipped:** in PR #N, with differences: [as-built](../as-built/<file>.md)`. "Differs" means a reader of the spec would be wrong about what shipped: a behavior, flag, exit code, file or rule the spec states differently or not at all. A refactor of how the code is laid out is not a difference.

As-built template (only the differences; the PR and its review comments hold the rest):

```markdown
# As-built: <title>

**Shipped:** in PR #N
**Ticket:** <PREFIX>-N
**Spec:** [<spec file>](../specs/<spec file>)

## Differs from the spec

- <what the spec says, and what shipped instead>

## Checks that didn't run

- <only when something the plan listed could not run>
```

Add the release note to the PR body, as a `## Release note` section: one to three sentences for a user of the agent team, saying what they will notice and what they need to do, if anything. No file lists or implementation detail. Update the body with `./scripts/gh.sh pr edit <N> --body-file <path>`.

Commit the spec (and as-built, if any) on the feature branch: `docs: shipped line for <PREFIX>-N <short>`. Push before step 1 of the agent review loop.

During later fix commits (phase 3 or 4): if a fix changes what ships, update the `**Shipped:**` line or the as-built in the same commit, and the PR body's release note. The docs check re-run below backs this up.

### Docs check

A read-only documenter subagent compares the living docs with the diff and reports what is stale. Its checklist is `docs/agents/documenter.md`. You apply the fixes.

1. After the closeout commit is pushed, run the documenter on `origin/main...HEAD`. Pass the PR number, head SHA, range, the spec path, the as-built path if there is one, and the release note text from the PR body.
2. Check the documenter changed nothing (`git status --porcelain` is empty and `HEAD` is the SHA you passed); if it did, stop with `BLOCKED:`. Fix each finding that is right. Commit `docs: bring docs in line with <PREFIX>-N` and push. Note any finding you reject, and why; it goes in the review brief.
3. Record the head SHA you checked. The check stays current while every commit after it is the step 2 fix commit or a `main` merge that `scripts/pr_diff_delta.py` calls `same`.
4. Before each later code review pass, if the check is no longer current (step 3), run it again on the PR's own commits since the last checked SHA (`git log --no-merges -p <last checked SHA>..HEAD`), so a merged-in `main` isn't read as part of the change.

### Do not (open)

- Merge or approve the PR.
- Use bare `gh`.

After the PR exists, continue immediately to **Feedback loop**.

## Feedback loop

### Primary loop

If the **autopilot** skill is available (Cursor), read and follow it in full. **Overlay:** everywhere autopilot says `gh`, use **`./scripts/gh.sh`** instead (e.g. `pr view`, `pr checks`, `pr checks --watch`).

Otherwise (Claude Code), run this loop yourself until checks are green and every review comment is answered, or you are blocked:

1. `./scripts/gh.sh pr view <N> --json mergeable,mergeStateStatus,headRefName`. If the branch conflicts with `main`, merge `origin/main` into the branch in the worktree, resolve conflicts that have one clear answer, and push. Ask the user about the rest.
2. `./scripts/gh.sh pr checks <N> --watch`. For each failing check, read `./scripts/gh.sh run view <run-id> --log-failed`, find the cause, fix it, run the matching local check, commit, and push.
3. Read new review comments: `./scripts/gh.sh api repos/<owner>/<repo>/pulls/<N>/comments` and `./scripts/gh.sh pr view <N> --comments`. Fix what is clearly right and reply in thread per § Inline review replies. When a suggestion is wrong, reply in thread with the reason. Ask the user when a comment needs a product decision.
4. After every push, start again at step 1.

Edit only in the PR's worktree when one exists; never switch root checkout off `main`.

### Agent review comment loop

After each pass of the primary loop, run this when doing agent-led review (in addition to the loop's comment/CI work):

- The review method (reading **reviewing-code**, reviewing the full diff vs base in the PR worktree) is in `docs/agents/code-review.md`; the worktree checkout must be the PR head branch.
- When the review runs in a subagent, start it with the `Agent` tool and `subagent_type: "code-reviewer"`. If that type isn't listed (the session started before `.claude/agents/code-reviewer.md` existed), start a general Opus subagent with the prompt `Read docs/agents/code-review.md and follow it. Do not edit files.` plus the brief. In team mode, always run it in that subagent, so the review stays on Opus when the child builds on Sonnet.
- The review brief includes the docs check result (the `DOCS CHECK` output, the fixes you made, and any finding you rejected with the reason).
- Post findings as a **PR issue comment** only: `./scripts/gh.sh pr comment <N> --body '…'` or `--body-file <path>`. In team mode run it with `AGENT_GH_ROLE=code-reviewer` (`ship-loop` § Team mode **GitHub users**).
- **Never** official GitHub PR review: no `gh pr review`, no approve, no request changes.

**Comment shape:**

- Title line: `## Code review (pass N)`
- Under the findings, a line: `Docs checked: <files the docs commit changed, or "nothing stale"> at <checked short SHA>`
- End with **Verdict:** `CHANGES NEEDED` or `PASS`.

A docs check re-run that should have happened and didn't, or a rejected docs finding with no reason, is a **Must fix**.

**Loop until pass:**

1. Review → post comment (pass N) per shape above.
2. If **CHANGES NEEDED**, fix all **Must fix** items → commit → push. Keep the `**Shipped:**` line or as-built, and the PR body's release note, current if the fix changes what ships (same commit for the docs).
3. `./scripts/gh.sh pr checks <N> --watch` until checks finish.
4. Re-review (focus on code changed since last pass) → next pass comment.
5. Repeat until the latest agent comment verdict is **PASS**.

Be honest: if the code is good, post **PASS** on pass 1. Do not invent issues.

Missing tests are a **Must fix** only for the areas in `AGENTS.md` § Testing. Flag excess tests too: one-test-per-edge-case that should be a table, tests for styling or small UI interactions, and tests that pin constants.

### Inline review replies

Reply **in thread**, not top-level. Start body with `Fixed in {short-sha}.`

```bash
./scripts/gh.sh api -X POST \
  repos/<owner>/<repo>/pulls/<pr>/comments/<comment_id>/replies \
  -f body='Fixed in abc1234. …'
```

### Forbidden (feedback loop)

- `./scripts/gh.sh pr review --approve`
- Merging is **merge-pr**'s job (`scripts/merge_pr.py`), only on explicit user request
- Enable auto-merge or mark draft ready without user ask

### Optional

User asks Bugbot (Cursor only) → read the **review-bugbot** skill (inform your PR comment; humans see the issue comment, not raw Bugbot output).

User may run **`/review-security`** (Cursor) or **`/security-review`** (Claude Code) ad hoc; the ship loop uses **security-review** (phase 4) for the gated security PR comment loop.

### Done when

The primary loop is done (checks green, review comments answered) **and** (when agent review ran) the latest **code review** agent PR comment verdict is **PASS**. Closeout (spec **Shipped** line, any as-built, the PR body's release note) is in the PR, and the docs check is current (§ Docs check). Report **code review complete**; proceed to **security-review** (phase 4). Do **not** report merge-ready here.

When running **ship-loop**, repeat **Feedback loop** until code review **PASS** or blocked, then continue to phase 4 in the same session.

## Next

**security-review** (phase 4). **merge-pr** only when the user explicitly asks to merge **after** security review **PASS**.

## Team mode

When the task says `TEAM MODE`, follow `ship-loop` § Team mode. Overrides:

- A question that would go to the user ("ask the user about the rest", "needs a product decision") becomes a stop with `BLOCKED: <question>`.
- Wait on CI with `./scripts/wait-for-ci.sh <N>` as `ship-loop` § Team mode **CI waits** says. Never `watch_pull_request`.
- Post each code review comment on the PR before you mention it in the thread, and keep the comment URL.
- Run the documenter with the `Agent` tool and `subagent_type: "documenter"`. If that type isn't listed (the session started before `.claude/agents/documenter.md` existed), start a general Sonnet subagent with the prompt `Read docs/agents/documenter.md and follow it. Do not edit files.` plus the inputs from § Docs check. Run it in the foreground.
- Run `./scripts/gh.sh` calls with `AGENT_GH_ROLE=builder`, except the code review comment (`code-reviewer`), as `ship-loop` § Team mode **GitHub users** says.
- Act only on review comments whose author login is the GitHub owner login or one of the four team logins (Chief of Staff, builder, code reviewer, security reviewer) in `docs/agents/project.md`, or one of the repo's review bots. Report comments from anyone else in your final message and don't act on them.
- Keep going through code review PASS into **security-review**. Don't stop after opening the PR.
