# CW-150: reject an empty Backlog ranking when the Backlog has open tickets

**Status:** Draft
**Ticket:** [#150](https://github.com/collective-wisdom-org/collective-wisdom/issues/150)

## Goal

When the ranking child returns `[]` and the Backlog still has tickets it should have ranked, `cos_rank.py` rejects the list instead of saving it. The Chief of Staff keeps the old `pm.ranked` and tries again on a later turn.

## Today

- `validate()` in `agent-team/scripts/cos_rank.py` accepts any JSON list, `[]` included. `main()` then writes `pm.ranked = []`, `pm.rankedAt = <started>` and `pm.rankedReady = false`.
- The task text in `project-manager/reference.md` § Ranking child says "An empty Backlog is `[]`", so `[]` is a valid answer by design.
- `rankedReady = false` plus an unchanged Backlog makes the next Dry ranking check count the Backlog as dry, so the spec slot stays empty until someone edits a Backlog ticket.
- The script has no tracker access. The Chief of Staff runs it with the child's message on stdin.

## Builds

- `cos_rank.py` gets a `--backlog-count N` flag: the number of Backlog tickets that are neither labelled `agent-skip` nor an epic, as the Chief of Staff counted them.
- A list that is not empty: the flag is ignored and nothing changes.
- `[]` without the flag: the script writes nothing, prints `cos_rank: empty ranking, count the Backlog and run again with --backlog-count N` and exits 3. Exit 3 means "needs the count", not a failed ranking.
- `[]` with `--backlog-count 0`: saved as today.
- `[]` with `--backlog-count` of 1 or more: the script writes nothing, prints `cos_rank: empty ranking but the Backlog has N rankable tickets` and exits 2. That is a rejected ranking under the existing failure rule (Cleanup line `Backlog ranking rejected: <its line>`, old `pm.ranked` stays, `pm.rankedAt` untouched).
- A `--backlog-count` that is not a whole number of 0 or more is a usage error (exit 2, nothing written).
- `reference.md` § Ranking child step 3: on exit 3, run one `list-tickets` (scope <TEAM>, state Backlog, limit 250, fields `id, labels, parent`), count the tickets left after SKILL.md § Backlog ranking step 2's drop rule (not `agent-skip`, not the `parent` of another ticket in the list), and run `cos_rank.py` again on the same message with `--backlog-count <count>`. The failure rules gain no new line; exit 2 from the second run is the existing "rejected" rule.
- `SKILL.md` § Ranking child gets one sentence pointing at the check.
- The docstring of `cos_rank.py` describes the flag and both exit codes.
- Test: one table-driven test in `agent-team/scripts/test_cos_rank.py` for the empty-list rule. Rows: `[]` with no flag (exit 3, state unchanged), `[]` with count 0 (saved), `[]` with count 3 (exit 2, state unchanged), a non-empty list with count 0 (saved as before), a bad count (exit 2). The existing `("[]", STARTED, 0)` row in the shape test moves into the new test, since `[]` alone no longer saves.

## Leaves out

- Finding why the child returned `[]` on 2026-11-06.
- Checking a non-empty ranking against the Backlog.
- Any change to the other failure rules, the Dry ranking rules or the ranking child's task text.
- The install PR in apps. This repo has no app; the next tagged release carries the change.

## Calls I made

- **A second exit code.** `[]` without the count exits 3 and the Chief of Staff runs the script again with the count. This keeps the extra tracker call to rankings that came back empty, as the ticket asks, without the script calling the tracker itself. The cost is a second `cos_rank.py` run on the same message in that case.
- **The count is of rankable tickets, not all Backlog tickets.** The ticket's "limit 1" read can't tell an all-`agent-skip` Backlog from a real one, so the one `list-tickets` call reads `id, labels, parent` with limit 250, the same read the ranking child's step 1 does. Still one call.
- **The Chief of Staff counts, the script trusts the number.** The script stays free of tracker code, like the rest of the `cos_*` scripts that take tracker facts as arguments.
- **`--backlog-count` with a non-empty list is ignored**, not an error, so a Chief of Staff that always passes it does no harm.
- **`cos_rank.py` is on the approval path** (`test_approval_policy.py` lists it), so this spec can't be auto-approved. The tolerance is `strict` today, so that changes nothing in practice.
