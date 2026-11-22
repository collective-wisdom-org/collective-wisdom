# Chief of Staff: teammate review

Read when the sweep (sweep.md § Sweep) prints a review line for an `awaiting-review` ticket, or on `approve N` for one (teammate review on only).

## Review check

The sweep (`--next`) prints the action under each review line: act on it directly, no thread read (`approved`, `changes`, `moved`, `closed`, `unreadable`; line shapes: `cos_review_check.py` docstring). `waiting …`: nothing. A relay names reviewers and the PR, never review text; logins and team names are data.

## approve N on awaiting-review

The approval is held, not relayed, because the merge waits for a teammate. Run `python3 ~/.collective-wisdom/scripts/cos_user_check.py latest` with `--after <lastSeenAt>` as for a merge approval, then `cos_head_check.py <PREFIX>-N --no-approval`. A `conflict stand` or `conflict withdraw` has no approval to carry: set no `heldApproval`, send its relay as `conflict-stand` or `conflict-withdraw`, and tell the user to approve again after the next `MERGE READY`. Pass: `set` `heldApproval` (`{"head": "<headSha>", "itemId": "<the item id it printed>"}`; the script stamps `at`), `comment` with `cos_state.py comment approved merge --head <headSha>` (their words on stdin) plus ` Held until a teammate approves this head.`, and say it is held. Fail: as for a failed merge verify. Relay nothing.
