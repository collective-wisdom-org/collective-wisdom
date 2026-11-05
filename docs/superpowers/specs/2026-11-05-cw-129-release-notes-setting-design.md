# CW-129: Make release note publishing a setting

**Ticket:** [CW-129](https://github.com/collective-wisdom-org/collective-wisdom/issues/129)
**Status:** Draft

## Goal

A repo that keeps its own changelog can turn release notes off. With them off, PRs carry no `## Release note` section, the merge gate doesn't ask for one, and nothing writes the `release-notes` branch. Repos that say nothing keep today's behaviour.

## Today

Facts from `main` at `59c9b12`, checked 2026-11-05.

- `open-pr` § Closeout docs asks for a `## Release note` section in every PR body. The documenter (`docs/agents/documenter.md` check 5) reviews its text.
- `scripts/merge_pr.py` `gate()` stops with `closeout missing: no "## Release note" section ...` when the body has no section and the PR adds no `docs/superpowers/release-notes/*.md`, and checks that any added note file starts with a dated heading. `main()` calls `publish()` after the fast-forward, which writes `RELEASE_NOTES.md` on the `release-notes` branch through the API.
- `read_facts()` reads `noCi` and `Owner login` from `project.md` in the current directory, which is the root checkout on `main`, so a PR can't change the rules it is merged under.
- The template (`agent-team/templates/project.md`) carries a Repo invariants bullet that makes `merge_pr.py` the one writer of the `release-notes` branch, and a § Docs `Release notes` row describing the section and the branch.
- `merge-pr` SKILL.md (Closeout in PR), `docs/superpowers/README.md` (Release notes, Merge gate) and `docs/agents/README.md` describe notes as always on.
- `install.sh` seeds `project.md` from the template only on a fresh install; `--update` never touches an app's `project.md`.

## Change

### The setting

A new row in § Docs of `agent-team/templates/project.md`:

```
| Publish release notes (`on` or `off`) | `off`. With `on`, each PR body has a `## Release note` section and every merge publishes all notes to `RELEASE_NOTES.md` on the `release-notes` branch (...). `scripts/merge_pr.py` is then the one writer of that branch; no agent, skill or other script writes it. Layout in docs/superpowers/README.md |
```

`project_config.release_notes_enabled()` reads it with the existing `value()`: `off` (any case) gives `False`; a missing row, `on`, or any other value gives `True`.

### `scripts/merge_pr.py`

- `read_facts()` sets `f["notesOn"] = project_config.release_notes_enabled()`, next to `noCi`. It fetches added note files only when it is on.
- `gate()`: when `notesOn` is false, skip the release note block (the section check and the dated heading check on added note files). The spec, as-built and `## Proof` checks stay.
- `main()`: call `publish()` only when `notesOn` is true. When off, the merge prints no publish line at all.
- The module docstring says publishing depends on the row.

`scripts/release_notes.py` doesn't change; it still prints notes when run by hand.

### Template

- The new row replaces the `Release notes` row in § Docs.
- The Repo invariants bullet about the `release-notes` branch goes; its rule moves into the new row's note, so it only reads as a rule where notes are on.
- The template seeds `off`.

This repo's own `docs/agents/project.md` gets the row set to `on` and keeps its invariant bullet and `Release notes` row, so nothing changes here and the setting is visible.

### Skills and docs

Each place that asks for or describes the release note says it applies only when `Publish release notes` is on:

- `open-pr` § Closeout docs (the paragraph that asks for the section) and the PR body bullet in § Create PR. Later mentions ("the PR body's release note") get "if any".
- `merge-pr` § Pre-merge checks, Closeout in PR, and its last sentence about publishing.
- `docs/agents/documenter.md` check 5: skip when off.
- `docs/superpowers/README.md` § Release notes and § Merge gate, and `docs/agents/README.md`'s release notes line.
- Passing mentions in `kickoff-feature`, `ship-loop` § Close and `security-review` get "if any" where the wording would otherwise demand a note.

### Test

One table-driven test in `test_merge_pr.py`, rows `missing`, `on`, `off`, `other` (say `maybe`). Each row writes a `project.md` with that row (or none) through `PROJECT_MD`, then checks:

- `gate()` on a PR body with no `## Release note` section: a `closeout missing ... Release note` line for missing, on and other; `None` for off.
- whether `main()` calls `publish()` after a successful merge: yes for missing, on and other; no for off.

## Next to CW-125, CW-127 and CW-128

Open PR #132 (CW-125) and the spec-stage tickets CW-127 and CW-128 also edit `merge_pr.py`, `test_merge_pr.py` and the template. This branch starts from `origin/main` and keeps its lines apart from theirs:

- The new row sits in § Docs, not § Git and GitHub where CW-125 and CW-127 add theirs.
- In `merge_pr.py` it touches only the `noCi` line's neighbour in `read_facts()`, the release note block in `gate()` and the `publish()` call in `main()`. It doesn't touch `FIELDS`, the base or mergeability checks.
- `release_notes_enabled()` goes after `no_ci()` in `project_config.py`; the new test goes at the end of `test_merge_pr.py`.

Whoever merges second merges `main` in and resolves any conflict.

## Leaves out

- Removing existing `release-notes` branches or `docs/superpowers/release-notes/` files in apps that turn notes off.
- Any change to `scripts/release_notes.py`.
- Changing the setting in installed apps; they have no row, so they stay on.

## Calls I made

- **This repo gets an explicit `on` row.** The ticket only says a missing row means `on`. Writing it down shows the setting where people look and costs nothing.
- **An unknown value reads as `on`, not as an error.** `on` is today's behaviour, so a typo keeps the stricter gate instead of stopping merges or silently dropping notes. No warning line is printed.
- **With notes off, the gate also ignores added `release-notes/*.md` files** (no dated heading check), since nothing reads them.
- **The template's invariant bullet moves into the row note** rather than staying as a conditional bullet, so a new app that keeps `off` has no rule about a branch it never uses.
- **Skills check the row by name** ("when `Publish release notes` in `project.md` § Docs is `off`") rather than calling a script; they already read `project.md` for other facts.
- **The test lives in `test_merge_pr.py`**, covering `release_notes_enabled()` through the gate and `main()`, instead of a separate `test_project_config.py` table, to keep to one test for the rule.
