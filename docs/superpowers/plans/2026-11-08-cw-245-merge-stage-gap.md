# CW-245 plan: close the gap between a merge and the ticket leaving the merge stage

Spec: `docs/superpowers/specs/2026-11-08-cw-245-merge-stage-gap-design.md` (approved by the user in the Chief of Staff thread). Tests per `AGENTS.md` § Testing: one table-driven test per rule, test lines no more than feature lines.

## Task 1: `agent-team/scripts/cos_merge_wait.py` and `test_cos_merge_wait.py`

Spec § Design 1. Pure `decide(ticket, gh_result)` plus a loop with injectable clock, sleep and gh runner. Reads state through `cos_state.load`, GitHub through `~/.collective-wisdom/scripts/gh.sh pr view <pr> --json state` (20 s timeout). Writes nothing. Last-line and exit-code table as in the spec. Tests: one table of `decide` cases, one loop test with fakes (open, open, merged; five failures; time out).

## Task 2: `cos_tick.py` and `cos_route.py` print the wait

`relay_lines` in `cos_tick.py`: after a `send <T> merge …` line for a ticket whose `parentThreadId` is set and is not the chief thread, add `merge-wait <T>`. `cos_route.py`: a `route: send merge` that prints a `moving:` line also prints `merge-wait: <T>` (before the route line); the `fallback:` line of a merge continuation adds "and start the merge wait". Update both docstrings. One table case in `test_cos_tick.py` and one in `test_cos_route.py` (merge prints it, build does not).

## Task 3: dashboard `buildApi`

Drop a status row whose id and state `pr` match a `merged` entry's id and `number`; recompute `count`; drop empty groups. One table-driven case in `api.test.ts` as in the spec.

## Task 4: docs

`chief-of-staff/SKILL.md` (description line, § Tools, § Tick `merge-wait` row and the `send` row pointer, new § Merge wait, § Merged check note), `continuation.md` (merge-lane fallback), `rotation.md` (take-over step 4 sub-step; retired-thread row). Keep the text short; the build ends with the compaction pass.

Verify: `python3 -I -m pytest -q agent-team/scripts`, the node test command from `AGENTS.md`, `shellcheck` unchanged.
