# As-built: Test the T3 Code fresh-context reset on the Chief of Staff thread

**Shipped:** in PR #330
**Ticket:** CW-315
**Spec:** [2026-11-14-cw-315-fresh-context-reset-test-design.md](../specs/2026-11-14-cw-315-fresh-context-reset-test-design.md)

## Differs from the spec

- The build did not stop for a run sheet and scratch thread IDs. The user ran the checks in `dbeallor/cw-scratch` on their own and reported the results in the Chief of Staff thread, and the Chief of Staff relayed them. The build read no scratch thread, scratch state or store rows from the run. The run entry says so, and its check lines are the user's report, not quoted tool output. The build did only the schema read in check 4, on this machine's store.
- Check 1's context sizes are the two numbers the user gave, 83,815 and 88,851 (+6%). The report does not say which turn each is from, so the entry records them as reported and does not show a separate fresh-thread comparison.
- Only Claude Code ran. Checks 2 to 4 on Codex and Cursor (check 7) are `not run`, and the matrix row is `untested` for Codex, Cursor and Antigravity.
- The Claude Code cell in the Matrix 1 row is `partial`, not `works`, although checks 1 to 3 passed. Check 3's merge-wait case was closed out by the notice path, because take-over step 4.2 starts no merge wait when the ticket's parent is the chief itself, so a merge-wait wake across a reset is untested (G26). The queued `/compact` also truncates the skill (G25).
- Two gap lines name tickets the Chief of Staff filed from the run, [#328](https://github.com/collective-wisdom-org/collective-wisdom/issues/328) (G27) and [#329](https://github.com/collective-wisdom-org/collective-wisdom/issues/329) (G25), where the spec says `Ticket: none yet`. G26 and G28 have none.
- G27 is a finding, not a failed check: check 5 passed. The spec makes a gap only of a failed or partial check; this one is recorded because the run turned it up and a ticket exists.
