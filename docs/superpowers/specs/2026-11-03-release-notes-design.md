# Release notes in the PR closeout docs (design)

**Status:** Draft
**Ticket:** CW-13

## Intent

Every PR ships a short release note that says, in plain words, what changed for someone using the agent team. David can read all of them in one place. Agents never conflict on a shared file: one note file per ticket, joined at read time by a script, the same way the docs index works.

## Goals

- A release note file per ticket, written in the PR's closeout commit.
- `python3 scripts/release_notes.py` prints every note, newest first, in this repo and in an installed app.
- `scripts/merge_pr.py` refuses a PR with no release note, with a one-line cause.
- `open-pr`, `merge-pr`, the superpowers README and the documenter checklist say where the note goes.

## Non-goals

- Backfilling notes for past tickets.
- Version numbers, tags, or publishing the notes anywhere.
- Checking that the note's file name matches the PR's ticket.

## Design

### The note file

Path: `docs/superpowers/release-notes/<prefix>-N.md`, the same naming as the index file (`<prefix>` is the issue prefix in lower case). A doc PR with no ticket uses `release-notes/<YYYY-MM-DD>-<slug>.md`, as the index does.

Shape:

```markdown
# 2026-11-03 CW-13: Release notes in the closeout docs

Every PR now adds a short release note under `docs/superpowers/release-notes/`. Run `python3 scripts/release_notes.py` to read them all, newest first.
```

- First line: `# <YYYY-MM-DD> <PREFIX>-N: <title>`. The date is the day the closeout commit is written (the merge date isn't known yet).
- Body: one to three sentences for a user of the agent team, not for a reviewer. What they will notice, and what they need to do, if anything. No file lists or implementation detail; those live in the as-built.

### Print script: `agent-team/scripts/release_notes.py`

Modelled on `docs_index.py`, and finds the folder the same way (`Path(__file__).absolute().parent.parent`), so it works through the root `scripts` link here and from a real `scripts/` folder in an app.

- Reads every `docs/superpowers/release-notes/*.md`.
- Prints `# Release notes`, then each note with its heading turned into `## …`, blank line between notes.
- Order: date descending; on the same date, file name descending with numbers compared as numbers (`cw-13` before `cw-9`).
- A file whose first line isn't a dated heading is printed after the dated ones, as-is, and the script writes `release-notes: <file> has no dated heading` to stderr. Exit 0.
- No folder or no files: prints `# Release notes` and `No release notes yet.` Exit 0. That is the state of every installed app until its first closeout.

### Merge gate: `merge_pr.py`

After the index checks, the gate needs a release note in the PR:

- At least one file matching `docs/superpowers/release-notes/[^/]+\.md` with change type `ADDED`. Otherwise: `closeout missing: no added docs/superpowers/release-notes/*.md in the PR`.
- `read_facts` fetches its content at the head, like specs and the index. Its first non-empty line must match `# YYYY-MM-DD <text>`. Otherwise: `closeout missing: release note <path> has no '# YYYY-MM-DD <title>' heading`.

### Docs

- `open-pr` § Closeout docs: add the release note to the closeout list and to the closeout commit (`docs: as-built for <PREFIX>-N <short>` now includes it), with the shape above. § Docs check passes its path to the documenter. § Done when lists it.
- `merge-pr` § checks: the closeout line names the release note.
- `docs/superpowers/README.md` (shared, in `agent-team/`): a "Release notes" section with the path, the shape, the print command and the merge gate.
- `agent-team/docs/agents/documenter.md`: Inputs include the release note path; a checklist item says the note exists, has the dated heading, and describes what ships at the head SHA in user terms.
- `agent-team/templates/project.md` and this repo's `docs/agents/project.md`: a `Release notes listing` row under Commands, next to `Docs index listing`.
- This PR writes its own note, `docs/superpowers/release-notes/cw-13.md`.

### Install

`install.sh` already syncs `scripts/` and every skill and role doc, so the script, `open-pr`, `merge-pr` and the documenter reach apps with no change. The release notes folder isn't created by the installer; the first closeout creates it, and the print script handles its absence.

## Tests

Per AGENTS.md § Testing:

- `test_merge_pr.py`: the green fixture gains a release note; two rows join the existing `test_gate` table (no note, note without a dated heading).
- `test_release_notes.py`: one table-driven test over a temp folder: ordering (date, then numeric file name), undated file last with the stderr warning, missing folder.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` passes.
- `python3 scripts/release_notes.py` in this worktree prints the CW-13 note.
- `./install.sh --dry-run` into a scratch git repo lists `scripts/release_notes.py`, and running the installed script there prints `No release notes yet.`

## Calls I made

- `install.sh` still only seeds `docs/superpowers/README.md` when it's absent, so apps installed before this change keep their old README without the release notes section. The skills, which agents actually follow, do update. I didn't make the installer overwrite or flag that README, since apps may have edited it.
- The note's date is the closeout date, written in the heading, not the merge date. The print script sorts on it, not on git history, so it works on any checkout.
- The gate checks that a note exists and has the dated heading, not that its file name matches the ticket. The skill sets the name; the documenter checks it.
- The note must be `ADDED` in the PR, like the as-built, so a PR can't pass by editing an older ticket's note.
- A malformed note doesn't stop the print script; it goes last with a stderr warning, so one bad file never hides the others.
- Script name `release_notes.py`, folder `docs/superpowers/release-notes/`.
