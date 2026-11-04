# Superpowers

Design and build history for the project. Specs come before plans. As-built notes come after a milestone ships.

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
