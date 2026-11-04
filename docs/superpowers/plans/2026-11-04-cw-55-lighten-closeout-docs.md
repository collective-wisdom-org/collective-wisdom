# CW-55: Lighten the closeout docs per ticket: Implementation Plan

**Spec:** [2026-11-04-cw-55-lighten-closeout-docs-design.md](../specs/2026-11-04-cw-55-lighten-closeout-docs-design.md)

Two independent tasks (disjoint files). Verification at the end: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh`.

## Task 1: scripts and tests

Files: `agent-team/scripts/merge_pr.py`, `release_notes.py`, `docs_index.py`, `test_merge_pr.py`, `test_release_notes.py`, new `test_docs_index.py`, `test_symlinked_root.py`.

1. `merge_pr.py`: add `body` to `FIELDS`; replace the as-built, index and release-note closeout checks per spec § 4 (spec Shipped; "as specified" line naming this PR, or an added as-built file; `## Release note` body section, or an added dated note file; index checks removed). `read_facts` no longer fetches index files.
2. `release_notes.py`: disk notes as today, plus merged-PR `## Release note` sections per spec § 2 via `gh.sh`; exit 1 with stderr line when `gh.sh` fails.
3. `docs_index.py`: generate the table from `specs/`, `plans/`, `as-built/` per spec § 3.
4. Tests, one table each, per spec § Tests.

## Task 2: skills and docs

Files under `agent-team/`: `.claude/skills/{open-pr,merge-pr,kickoff-feature,ship-loop,security-review}/SKILL.md`, `docs/agents/documenter.md`, `docs/superpowers/README.md`, `templates/project.md`; plus `docs/agents/project.md` rows. Per spec § 5 and § 6. Delete `docs/superpowers/index/` and `agent-team/docs/superpowers/index/`.
