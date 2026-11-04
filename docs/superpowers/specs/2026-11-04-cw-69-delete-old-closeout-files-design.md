# CW-69: Delete the old-shape CW-55 and CW-51 closeout files

**Ticket:** [CW-69](https://github.com/dbeallor/collective-wisdom/issues/69)
**Status:** Draft

## Goal

PR #66 (CW-55) and PR #64 (CW-51) merged under the old closeout gate, so they shipped files the new shape no longer uses. Two problems follow:

- `docs/superpowers/release-notes/cw-55.md` repeats the `## Release note` section of PR #66, so `python3 scripts/release_notes.py` prints the CW-55 note twice.
- `docs/superpowers/index/` still holds hand-written index files. `scripts/docs_index.py` builds the index from `specs/`, `plans/` and `as-built/` and never reads `index/`. Nothing else in `agent-team/scripts/` or `install.sh` reads it either.

## Change

Delete four files:

- `docs/superpowers/release-notes/cw-55.md`
- `docs/superpowers/index/cw-51.md`
- `docs/superpowers/index/cw-55.md`
- `docs/superpowers/index/cw-65.md`

With all three index files gone, git drops the `docs/superpowers/index/` folder.

No script, skill, role doc or test changes. This is a markdown-only ticket, so it skips the plan and builds from this spec.

## Keep

- `docs/superpowers/release-notes/cw-51.md` and `cw-65.md`. PR #64 and PR #67 have no `## Release note` section, so each file is the only copy of its note.
- Every other file under `release-notes/`. Older notes stay by design.
- Mentions of `docs/superpowers/index/` in older specs and plans. They record what those tickets did at the time.

## Acceptance

- `python3 scripts/release_notes.py` prints the CW-55 note once (the one from PR #66's body).
- `python3 scripts/docs_index.py` runs and still lists the CW-51, CW-55 and CW-65 specs, plans and as-builts.
- `docs/superpowers/index/` no longer exists.
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Calls I made

- **Also delete `index/cw-65.md`.** The ticket names only the CW-51 and CW-55 index files and says deleting them empties `index/`. A third leftover, `index/cw-65.md` from PR #67 (CW-65), is there too. It is the same kind of hand-written index file, `docs_index.py` already lists the CW-65 docs without it, and the ticket's goal is an empty `index/`. Leaving it would keep the folder alive for one stale file.
- **Keep `release-notes/cw-65.md`.** I checked PR #67's body: it has no `## Release note` section, so this file is not a duplicate.
- **No new test.** Nothing in code changes. The acceptance checks are commands to run once, and a test that asserts a file is absent would only restate this PR.
- **Leave old specs and plans alone.** Their mentions of `index/` describe past work, not current rules.

## Out of scope

- Sorting release notes by PR merge time: #41.
- Old `index/` files in apps that installed the agent team. The CW-55 release note already tells app owners they can delete them.
