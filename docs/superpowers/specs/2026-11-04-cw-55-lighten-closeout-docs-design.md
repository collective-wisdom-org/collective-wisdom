# CW-55: Lighten the closeout docs per ticket

**Ticket:** [CW-55](https://github.com/dbeallor/collective-wisdom/issues/55)
**Status:** Shipped
**Shipped:** in PR #66, with differences: [as-built](../as-built/2026-11-04-cw-55-lighten-closeout-docs.md)

## Goal

Today every ticket ships five docs: spec, plan, as-built, an index file and a release note. For a small change the closeout outweighs the change. Keep the record and cut the ceremony:

- When the build matches the spec, the as-built is one line in the spec. A separate as-built file exists only when something differs, and it holds only the differences.
- The release note is a `## Release note` section in the PR body, not a file.
- The index is generated from the docs themselves. Nobody writes index rows by hand any more.
- `scripts/merge_pr.py` gates on the new shape, and still accepts the old shape so PRs already open keep merging.

## Non-goals

- Backfilling or rewriting existing as-built files, specs or release notes.
- Changing what the code review, security review or documenter check (CW-54 covers review cost).
- Changing how `install.sh` copies `docs/superpowers/README.md` (it adds the file only when the app has none).
- Editing the user-level `superpowers-project-memory` skill. It is not in this repo; the overrides in `open-pr` replace the parts that conflict.

## Design

### 1. As-built line in the spec

At closeout the child edits the spec header:

```markdown
**Status:** Shipped
**Shipped:** in PR #57, as specified
```

When the build differs from the spec, the line links a short as-built file instead:

```markdown
**Status:** Shipped
**Shipped:** in PR #57, with differences: [as-built](../as-built/2026-11-04-cw-55-lighten-closeout-docs.md)
```

That as-built file keeps the dateless `**Shipped:** in PR #N`, `**Ticket:**` and `**Spec:**` header lines, then one section, `## Differs from the spec`, with a bullet per difference. An optional `## Checks that didn't run` section follows when something listed in the plan could not run. No "What shipped", "How it was built" or "Verified" sections: the PR and its review comments hold those.

"Differs" means a reader of the spec would be wrong about what shipped: a behavior, flag, exit code, file or rule the spec states differently or not at all. A refactor of how the code is laid out is not a difference.

### 2. Release note in the PR body

The PR body gets a section:

```markdown
## Release note

`install.sh --update <app>` now moves an app to the newest commit and reports what changed.
```

One to three sentences for a user of the agent team, same rules as today's note files. The text runs from the heading to the next `## ` heading or the end of the body. The child writes it in the closeout step and keeps it current when a fix changes what ships, as it does today with the note file.

`scripts/release_notes.py`:

- Prints the notes on disk exactly as today (same order, same headings, same undated warning).
- Also reads merged PRs into `main` through `./scripts/gh.sh pr list --state merged --base main --json number,title,body,mergedAt --limit 500`, keeps the ones whose body has a non-empty `## Release note` section, and prints each as `## <merge date, UTC> <title> (#N)`, followed by the section text. `<title>` is the PR title with a leading conventional-commit prefix (`feat:`, `fix(x):` and so on) removed.
- Merges both lists into one, dated notes newest first, by date then by name (files) or PR number (PR notes), the same rule the file sort uses today. Undated file notes stay last.
- When `gh.sh` fails (no auth, offline), it prints the notes on disk, writes `release-notes: cannot read merged PRs: <reason>` to stderr and exits 1.

### 3. Generated index

`scripts/docs_index.py` stops reading `docs/superpowers/index/*.md`. It scans `specs/`, `plans/` and `as-built/` under `docs/superpowers/` and prints the same three-column table it prints today:

| Column | Source |
|---|---|
| Date | the `YYYY-MM-DD` prefix of the file name |
| Type | `Spec`, `Plan` or `As-built`, from the folder |
| Doc | `[<first # heading, without a leading "As-built: ">](<folder>/<file>)` |

Sorted by date, then type (spec, plan, as-built), then file name. A file with no dated name is listed last with an empty date and a warning on stderr. A file with no `# ` heading uses its file name as the title.

The hand-written index files go away: this PR deletes `docs/superpowers/index/` in this repo and `agent-team/docs/superpowers/index/`. Apps keep theirs until someone deletes them; nothing reads them after the update, and the release note says so.

### 4. Merge gate

`gate()` in `scripts/merge_pr.py` replaces its closeout checks with these, in order. `FIELDS` gains `body`.

1. A spec in the PR has `**Status:** Shipped` (unchanged).
2. As-built: a spec in the PR has a line matching `**Shipped:** in PR #<this PR>, as specified`, **or** the PR adds a file under `docs/superpowers/as-built/`. Stop reason: `closeout missing: no spec says "**Shipped:** in PR #N, as specified" and no added docs/superpowers/as-built/*.md`.
3. Release note: the PR body has a non-empty `## Release note` section, **or** the PR adds a `docs/superpowers/release-notes/*.md` file whose first line is a dated heading (today's check). Stop reason: `closeout missing: no "## Release note" section in the PR body and no added release note file`. An added note file with no dated heading still stops with today's reason.
4. The index checks (an `index/` file in the PR, and one that links the as-built) are removed.

The "or" branches keep PRs opened before this change mergeable, and keep the gate working for an app that installs this before it changes habits.

### 5. Plan for markdown-only tickets

A ticket whose change touches only markdown files (docs, skills, role docs) may skip the plan: the spec is enough, and the build stage goes straight to building. A ticket that changes a script, a test, `install.sh` or config writes a plan as today. Together with sections 1 to 3, a markdown-only ticket that ships as specified merges with a spec (plus its `**Shipped:**` line) and a PR body, and nothing else.

### 6. Skill and doc updates

All under `agent-team/` unless noted.

- `.claude/skills/open-pr/SKILL.md`: § Superpowers docs (no index rows; the plan may be absent per section 5), the PR body overlay (spec path, `## Release note` section, as-built path only when one exists), § Closeout docs rewritten to sections 1 and 2 with the as-built template inline, the fix-commit rule (update the `**Shipped:**` line or as-built and the PR body's release note), § Docs check inputs, § Done when.
- `.claude/skills/merge-pr/SKILL.md`: the checks list and "Closeout in PR" paragraph.
- `.claude/skills/kickoff-feature/SKILL.md`: drop index rows from step 2 and the "Start now" path; note the plan rule from section 5 in § Team mode.
- `.claude/skills/ship-loop/SKILL.md`: § 6 Close and its index line; the Build stage line "Write the plan" points to the section 5 exception.
- `.claude/skills/security-review/SKILL.md`: the "update the as-built" line also covers the `**Shipped:**` line and the release note section.
- `docs/agents/documenter.md`: inputs (spec path, as-built path if any, release note text from the PR body, no index file); checklist items 2, 4 and 5 rewritten to match.
- `docs/superpowers/README.md`: rewritten for the new layout (`docs/superpowers/README.md` at the root links to it).
- `templates/project.md` Docs and Commands rows for the index and release notes; the same rows in this repo's `docs/agents/project.md`.

### Tests

Per `AGENTS.md` § Testing, one table-driven test per rule:

- `test_merge_pr.py`: the existing `test_gate` table gets rows for the new closeout rules (as-specified line passes with no as-built file, wrong PR number fails, added as-built passes without the line, body section passes with no note file, empty section fails, old note file still passes). The two index rows go.
- `test_release_notes.py`: one table over files only, PRs only, both interleaved by date, and a failing `gh.sh` (disk notes still printed, stderr line, exit 1). The existing order test keeps passing unchanged, which covers "output unchanged for notes on disk".
- `test_docs_index.py` (new): one table over a temp `docs/superpowers` with a spec, plan and as-built, an undated file and a file with no heading.
- `test_symlinked_root.py`: the `docs_index` row points at `docs/superpowers` instead of `docs/superpowers/index`.

## Acceptance

- A markdown-only ticket that ships as specified merges with a spec and a PR body and nothing else: `merge_pr.py` passes a PR whose only closeout is the spec's `**Shipped:** in PR #N, as specified` line and a `## Release note` section.
- A ticket that differs from its spec has an as-built file listing the differences, linked from the spec's `**Shipped:**` line.
- `release_notes.py` prints the notes on disk as before and adds the notes from merged PR bodies.
- `docs_index.py` lists every spec, plan and as-built without any index file.

## Calls I made

- **Markdown-only tickets may skip the plan.** The ticket's acceptance says a docs-only ticket ships with "a spec and a PR body and nothing else", which rules out a plan file. I read "docs-only" as any change to markdown files only, which includes skills and role docs. A narrower reading (only `docs/` and `README.md`, as CW-54 defines it) would still require plans for skill-only tickets.
- **The gate keeps accepting the old shape.** An added as-built file still satisfies the as-built check, and an added dated note file still satisfies the release note check. Without this, every PR open at merge time, and every app that updates mid-ticket, would fail the gate until it was redone.
- **Generated index, and the index files are deleted in this repo.** The ticket allowed either generating rows into the files or dropping the files. Generating from the doc folders needs no per-ticket file at all, so I drop them. Titles in the printed table change to each doc's own heading.
- **Release notes come from merged PR bodies, not from a merge-time append to `RELEASE_NOTES.md`.** An append at merge time would mean `merge_pr.py` committing to `main`, which the repo forbids.
- **`release_notes.py` exits 1 when it cannot read PRs**, after printing the notes on disk, so a caller can tell the list is incomplete. Today it always exits 0.
- **PR note title is the PR title minus its conventional-commit prefix**, plus `(#N)`. No separate title line in the section.
- **The last 500 merged PRs** are read. That covers this repo many times over; a repo with more would lose its oldest PR notes from the listing.
- **The `**Shipped:**` line must name this PR's number** for the "as specified" path, so a line copied from another spec doesn't pass.
- **`**Status:** Shipped` stays** alongside the new `**Shipped:**` line, since the documenter and existing specs use it.
- **This spec has an index file** (`docs/superpowers/index/cw-55.md`), because the rule on `main` still asks for one at kickoff. The build deletes it with the rest.

## Leaves out

- Apps' copies of `docs/superpowers/README.md` stay stale after `install.sh --update`, since the installer adds that file only when it is missing. The release note tells app owners to copy it over by hand.
