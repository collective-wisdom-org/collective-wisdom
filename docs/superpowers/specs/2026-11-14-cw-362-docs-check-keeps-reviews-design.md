# CW-362: Keep the code and security reviews when only the docs check changed the head

**Status:** Shipped
**Shipped:** in PR #377, with differences: [as-built](../as-built/2026-11-14-cw-362-docs-check-keeps-reviews.md)
**Ticket:** [#362](https://github.com/collective-wisdom-org/collective-wisdom/issues/362)

## Goal

The docs check runs once, after both reviews PASS, and its fix commit moves the head. When that commit changes only the living docs the documenter checks, the reviews from the head before it stand: `review_gate.py` prints the reviews-stand `note`, not `rerun both`, and `merge_pr.py` merges on that note. Any other head move is judged as today. When the gate can't tell, it runs the reviews.

## Today

Facts from `main` at `2c1ea0c`.

- `open-pr` § Docs check step 2: the child applies the documenter's findings, commits `docs: bring docs in line with <PREFIX>-N` and pushes. Step 4 runs `review_gate.py`.
- `pr_diff_delta.delta(reviewed, head)` compares the PR's diff at both heads per file and returns `same`, `docs` or `changed`. `docs` needs every differing file to pass `is_docs`: an ASCII `.md` that is `README.md` at the top or under `docs/` but not `docs/agents/`, no hidden path part, not `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md`, regular file mode on both sides.
- `merge_pr.stands` and `review_gate.verdict` accept `same` and `docs`. Both call the same `delta`, so the gate and the pre-check can't disagree. The note text is only a pointer: `stands` re-runs `delta` at merge and decides from that.
- This repo's living docs (`project.md` § Docs check) are `README.md`, `AGENTS.md`, `docs/agents/project.md`, `agent-team/docs/agents/` and `agent-team/.claude/skills/`. Only `README.md` passes `is_docs`, so nearly every docs-check fix here prints `rerun both`.
- `cos_brief.py`'s `moved_line` reads the `Head moved to` note with `MOVED_RE` and prints `head moved by docs-file changes only since <sha>; reviews stand`.
- `cos_review_check.py` deals only with teammate GitHub reviews (`merge_pr.review_stop`) and the ticket's `headSha`, which is the head in `MERGE READY`. The docs check runs before `MERGE READY`, so its head move never reaches this script. It needs no change.

## Design

### A third kind: `living`

`pr_diff_delta.delta` gains a kind, `living`, checked only when the result would otherwise be `changed`. It needs all of these, and any failure gives `changed` (never an error that skips reviews):

1. **One fix commit.** `git rev-list --parents <reviewed>..<head>` is exactly one commit, it has exactly one parent, and that parent is the reviewed head. A merge of the target branch, a second commit, or a rebase fails this.
2. **The fix commit's subject.** `git log -1 --format=%s <head>` is exactly `docs: bring docs in line with <PREFIX>-<N>`, with `<PREFIX>` from `project.md` and `<N>` digits.
3. **Living docs only.** Every file that differs between the two PR diffs is either a docs file (`is_docs`) or a living doc:
   - it matches an entry on the `Living docs to search:` line of `project.md` § Docs check, **as committed on `origin/<target>`** (read the way `project_config._committed_rows` reads, never from the working tree, so a PR can't widen its own list). An entry ending in `/` matches any path under it; any other entry matches only that exact path. Only backticked entries count, so the template's `<add ...>` placeholder matches nothing.
   - it is an ASCII-named `.md` file with no `..` part, a regular file (mode `100644` or absent) on both sides, as `is_docs` checks.
   - it is **not on the hands path** (`approval_policy.on_hands_path`). That keeps out `docs/agents/project.md`, `AGENTS.md` and `CLAUDE.md` at any depth, the gate skills (`chief-of-staff`, `ship-loop`, `open-pr`, `security-review`, `merge-pr` and the security skills) and the reviewer role docs. A docs-check fix to any of those still reruns both reviews.

A read failure in steps 1 to 3 (git, an unreadable or unparseable `project.md` on `origin/<target>`) gives `changed`. The docstring and the exit-0 line list gain `pr-diff-delta: living since <reviewed> at <head>: <file>, ...`.

`same` and `docs` keep their rules and win first: a fix commit touching only `docs/superpowers/` files still prints `docs`.

### `review_gate.py`

`verdict` accepts `living` beside `same` and `docs`, and prints the note:

```
Head moved to <head> by the docs check fix commit; PR diff changed only in living docs since <reviewed>: <files>. Reviews from <reviewed> stand.
```

`<files>` is `pr_diff_delta.show(files)`. The docstring's `note` row says so.

### `merge_pr.py`

- `NOTE` matches the new wording too: a third anchored alternative, `by the docs check fix commit; PR diff changed only in living docs since`, before the reviewed SHA.
- `stands` accepts `living` from `delta`. Since `stands` re-runs `delta`, a hand-written note can't make a non-`living` head pass.
- The docstring's reviews-stand line names the living-docs rule.

### `cos_brief.py`

`MOVED_RE` gets the same third alternative and `moved_line` prints `head moved by the docs check fix commit since <sha>; reviews stand <url>` for it. The header line naming the docs-file note names this one too.

### Skills

- `open-pr` § Docs check step 4: the `note` also covers the docs check's own fix commit when it changes only living docs off the hands path; keep the commit subject exactly as step 2 gives it and push it as one commit on the reviewed head, with nothing else in it. A fix to a file on the hands path, or a commit that also changes anything else, gets `rerun`.
- `ship-loop` phase 4's `note` sentence names the docs-check fix commit beside the merge of the target branch and the docs-file change.

### Tests

Table-driven, one test per rule, in the existing suites:

- `test_pr_diff_delta.py`: one table over `delta` with a fake `run`: fix commit on living docs only → `living`; same plus a script → `changed`; a hands-path file (`docs/agents/project.md`, `agent-team/.claude/skills/open-pr/SKILL.md`) → `changed`; wrong subject → `changed`; two commits → `changed`; merge commit → `changed`; a living-docs list read failure → `changed`; a non-`.md` living doc → `changed`; `docs/superpowers/` only → `docs` (unchanged).
- `test_review_gate.py`: one row, a `living` delta prints the new note and `note head ...`.
- `test_merge_pr.py`: a row in the existing `stands` table: the new note with a `living` delta stands; the same note with a `changed` delta does not.
- `test_cos_brief_moved.py`: a row for the new note in its existing table.

## Leaves out

- Running the docs check more than once per PR.
- What the documenter reports.
- Any other head move: a fix commit combined with a target-branch merge, a second docs commit, or the docs fix in `ci` review mode.
- `cos_review_check.py`: no change (see Today).
- Non-`.md` living docs, such as an env example file: they still rerun.

## Calls I made

- **Skills and role docs count as living docs, except the ones on the hands path.** The ticket left this to the approver. Excluding all agent text would leave the change nearly useless here, since this repo's living docs are mostly skills. The hands path already names the files that decide approvals, reviews and merges, so a docs-check edit to those still reruns both reviews, and an edit to any other skill or role doc keeps them. The note lists every file, and the user sees it in the merge block.
- **The fix commit is recognised by git, not by comments.** One commit whose only parent is the reviewed head, with the exact subject from `open-pr` step 2. The subject alone proves nothing against a builder that lies, but the file rule does the real work; the commit rule stops the exception covering other pushes that happen to touch living docs.
- **The living-docs list is read from `origin/<target>`,** so a PR can't add paths to its own exception.
- **Only `.md` living docs count.** An env example or config file listed as a living doc can change behaviour.
- **Failures fall back to `changed`, not exit 2,** so a read problem in the new check costs a review rerun, never a skipped one, and doesn't break today's `same` and `docs` results.
- **`cos_review_check.py` is left alone,** although the ticket names it: it never sees agent reviews or the pre-`MERGE READY` head move.
- **No `## Docs check` comment check.** The builder writes both the comment and the commit, so the comment adds no proof.

## Files

- `agent-team/scripts/pr_diff_delta.py`, `agent-team/scripts/project_config.py` (read the living-docs line from `origin/<target>`), `agent-team/scripts/review_gate.py`, `agent-team/scripts/merge_pr.py`, `agent-team/scripts/cos_brief.py`
- `agent-team/scripts/test_pr_diff_delta.py`, `test_review_gate.py`, `test_merge_pr.py`, `test_cos_brief_moved.py`
- `agent-team/.claude/skills/open-pr/SKILL.md`, `agent-team/.claude/skills/ship-loop/SKILL.md`
