# As-built: Cursor sessions in the usage and cost report

**Shipped:** in PR #269
**Ticket:** CW-257
**Spec:** [2026-11-08-cw-257-cursor-usage-report-design.md](../specs/2026-11-08-cw-257-cursor-usage-report-design.md)

## Differs from the spec

- A Cursor store that cannot be opened, or a run whose usage cannot be parsed, makes `--ticket` print `cost unknown (... cannot read a Cursor store ...; $X priced)` for a ticket that has a session, instead of skipping it silently. A ticket with no session still exits 2. The window report skips it with a stderr line.
- The window report has no test. The spec's Tests section asked only for the `--ticket` and stage-split tests.
- A Cursor session adds only its runs' start times to the wall span, so a one-turn Cursor session adds no wall time.
- The `Branch:` line is read up to the first `.`, because the child task reads `feat/...-slug. Create it yourself`. The `git branch` fallback runs only for worktree directories.
- `no_hands.py` builds the recorded end reason from the stop line, so it drops the `(<PREFIX>-N)` part: the reason stays `cost-unknown`. `no-hands.md` tells the Chief of Staff to pass `end` the reason without the ticket.
- `docs/compatibility.md`: the Codex and Antigravity cells now read "reads Claude Code and Cursor runs only (G8)", since "Claude Code transcripts only" is no longer true.
