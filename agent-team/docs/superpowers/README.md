# Superpowers

Design and build history for the project. A spec comes first, then a plan. When the PR ships, the spec says so.

## Layout

- `specs/`: one design spec per ticket.
- `plans/`: the implementation plan. A ticket that changes only markdown files (docs, skills, role docs) may skip it. A ticket that changes a script, a test, `install.sh` or config writes one.
- `as-built/`: written only when the build differs from the spec.

Files are named `<YYYY-MM-DD>-<slug>...md`. There are no index files to edit.

`python3 ~/.collective-wisdom/scripts/docs_index.py` prints every spec, plan and as-built as one table sorted by date. The title is the doc's first `# ` heading.

## Closeout

When the PR exists, the child edits the spec header:

```markdown
**Status:** Shipped
**Shipped:** in PR #57, as specified
```

When the build differs from the spec, the line links an as-built file instead:

```markdown
**Shipped:** in PR #57, with differences: [as-built](../as-built/<date>-<slug>.md)
```

The as-built holds only the differences: the dateless `**Shipped:** in PR #N`, `**Ticket:**` and `**Spec:**` lines, then `## Differs from the spec` with a bullet per difference. What did not run goes in the PR's `Not proven` list (`open-pr` § Proof). "Differs" means a reader of the spec would be wrong about what shipped: a behavior, flag, exit code, file or rule the spec states differently or not at all. A refactor of how the code is laid out is not a difference.

## Release notes

This applies only when `Publish release notes` in project.md § Docs is not `off`; a missing row counts as `on`. With `off`, PRs carry no release note, the merge gate does not ask for one and nothing is published.

The PR body has a `## Release note` section, one to three sentences for a user of the agent team: what they will notice and what they need to do, if anything. No file lists or implementation detail. The text runs from the heading to the next `## ` heading or the end of the body.

```markdown
## Release note

The Chief of Staff status table now links each ticket's child thread under its ID and title.
```

`python3 ~/.collective-wisdom/scripts/release_notes.py` prints every note, newest merge first: the files under `release-notes/` (older PRs) and the notes in merged PR bodies. Each note shows `Merged YYYY-MM-DD HH:MM UTC.` under its heading; a file note's time is when git added it on `origin/<merge target branch>`, and when git can't tell (no history, no `origin/<merge target branch>`, a renamed file, or a commit that added several notes at once) it sorts by its heading date and shows no time. A file note with no dated first line is printed last, with a warning on stderr. If it cannot read the merged PRs it prints the file notes, says why on stderr and exits 1. With no notes yet it prints `No release notes yet.` After each merge `~/.collective-wisdom/scripts/merge_pr.py` publishes the same text as `RELEASE_NOTES.md` on the `release-notes` branch.

## Merge gate

`~/.collective-wisdom/scripts/merge_pr.py` refuses to merge a PR unless:

- a spec in the PR has `**Status:** Shipped`;
- a spec has `**Shipped:** in PR #N, as specified`, or the PR adds a file under `as-built/`;
- unless `Publish release notes` in project.md § Docs is `off`: the PR body has a non-empty `## Release note` section, or the PR adds a `release-notes/` file; any added `release-notes/` file must start with a dated heading.

The file branches keep PRs opened under the old rules mergeable.
