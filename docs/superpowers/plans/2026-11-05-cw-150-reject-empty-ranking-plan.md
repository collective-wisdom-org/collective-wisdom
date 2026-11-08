# CW-150: reject an empty Backlog ranking: plan

**Spec:** [2026-11-05-cw-150-reject-empty-ranking-design.md](../specs/2026-11-05-cw-150-reject-empty-ranking-design.md)

All edits are under `agent-team/`. Test command: `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: test first

`agent-team/scripts/test_cos_rank.py`:

- Remove the `("[]", STARTED, 0)` row from `test_ranking_shape_check`. The fenced-block row stays (it ends in a non-empty list).
- Make `run()` accept extra CLI args (`extra=()`), appended to the `main()` argv.
- Add one table-driven `test_empty_ranking_needs_backlog_count`. Rows: `[]` no flag (exit 3, state unchanged, output starts `cos_rank: empty ranking, count the Backlog`), `[]` with `0` (exit 0, `pm.ranked == []`, `rankedAt == STARTED`, `rankedReady` false), `[]` with `3` (exit 2, state unchanged, output mentions `3 rankable tickets`), a non-empty list with `0` (exit 0, saved), `[]` with `-1` and with `abc` (exit 2, state unchanged, output starts `cos_rank: bad --backlog-count`).
- Run it and see the new rows fail.

## Task 2: script

`agent-team/scripts/cos_rank.py`:

- Add `--backlog-count`, default `None`, taken as a string. Check it next to `--started`: unless it is a whole number of 0 or more (`re.fullmatch(r"[0-9]+", s)`), print `cos_rank: bad --backlog-count` and return 2, writing nothing (the same shape as the bad `--started` check).
- After `validate()`, when `ranked == []`: no count prints `cos_rank: empty ranking, count the Backlog and run again with --backlog-count N` and returns 3; a count of 1 or more prints `cos_rank: empty ranking but the Backlog has N rankable tickets` and returns 2; a count of 0 falls through to the save. A non-empty list ignores the flag.
- Update the docstring: the flag, exit 3 ("needs the count"), the new exit 2 case.

## Task 3: docs

- `agent-team/.claude/skills/project-manager/reference.md` § Ranking child step 3: add the exit 3 handling as the spec describes (one `list-tickets`, scope <TEAM>, state Backlog, limit 250, fields `id, labels, parent`; count the tickets left after SKILL.md § Backlog ranking step 2; run `cos_rank.py` again on the same message with `--backlog-count <count>`). In the failure list, the exit 2 line covers the second run; add no new line. Mention in the exit 2 bullet nothing more than a short clause that this includes an empty list when the Backlog has rankable tickets.
- `agent-team/.claude/skills/project-manager/SKILL.md` § Ranking child: one sentence pointing at the empty-list check in `reference.md`.
- Prose follows `human-writing`: plain sentences, no em dashes.

## Task 4: verify

Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`. Commit as `feat: reject an empty Backlog ranking when the Backlog has tickets (CW-150)` and push.
