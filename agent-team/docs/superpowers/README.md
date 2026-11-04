# Superpowers

Design and build history for the project. Specs come before plans. As-built notes and release notes come after a milestone ships.

## Index

Entries live in `index/`, one file per ticket, so two PRs never edit the same lines.

- `index/<prefix>-N.md` (`<prefix>` is the issue prefix in lower case, from `docs/agents/project.md`) holds the rows for that ticket: spec and plan at kickoff, as-built at closeout.
- A doc with no ticket goes in `index/<YYYY-MM-DD>-<slug>.md`.

Each file is a three-column table. Links are relative to `index/`, so they start with `../`:

```markdown
| Date | Type | Doc |
|------|------|-----|
| 2026-11-02 | Spec | [Title (ABC-1)](../specs/<date>-<slug>-design.md) |
```

`python3 scripts/docs_index.py` prints every entry as one table sorted by date.

`scripts/merge_pr.py` refuses to merge a PR unless it adds a file under `as-built/`, marks a spec `**Status:** Shipped`, and includes an `index/` file that links the as-built.

## Release notes

Every PR adds one release note, in its closeout commit, that says in plain words what changed for someone using the agent team.

- `release-notes/<prefix>-N.md`, named like the index file. A doc with no ticket goes in `release-notes/<YYYY-MM-DD>-<slug>.md`.
- First line: `# <YYYY-MM-DD> <PREFIX>-N: <title>`, dated the day the closeout commit is written (a note with no ticket starts `# <YYYY-MM-DD> <title>`). Then one to three sentences for a user of the agent team: what they will notice and what they need to do, if anything. File lists and implementation detail go in the as-built.

```markdown
# 2026-11-03 ABC-1: Release notes in the closeout docs

Every PR now adds a short release note under `docs/superpowers/release-notes/`. Run `python3 scripts/release_notes.py` to read them all, newest first.
```

`python3 scripts/release_notes.py` prints every note, newest first. A note with no dated first line is printed last, with a warning on stderr. With no notes yet it prints `No release notes yet.`

`scripts/merge_pr.py` also refuses to merge a PR unless it adds a file under `release-notes/` whose first line is a dated heading.
