# Models: notes

Read this for why a role runs on its model, or for the Cursor, Codex or Antigravity notes.

### Claude Code

Why:

- Chief of Staff thread: bookkeeping; it reads children, the tracker and state and relays the user's words. The approval gates (the child's `createdBy: "user"` check, `approval_policy.py`, `cos_approve_pr.py`) don't rest on which model relays.
- Ticket helper: runs `write-ticket`; a wrong **Today** section costs an Opus spec run.
- Project manager children: read the tracker and rank or tidy it; the same tier as the Chief of Staff thread.
- Spec stage: the user approves the spec, so it needs the strongest model.
- Build and merge stages: work from an approved spec. Merge stays on this model: no second switch.
- Code review, security review: a missed bug costs more than the review.

Fable 5.1 and Haiku 5.5 are not used: they are not part of the default setup.

### Cursor

No Cursor run starts on a Claude model, Grok, Composer or Gemini; the team routes only to Auto (CW-275: the user's Cursor cannot pick models). Auto is the model `default` with no options, for every role. A subagent runs on `model: inherit` in its `.cursor/agents` file, so it takes its parent thread's model, which is Auto. The context window stays at Cursor's default.

Auto bills at the list price of the routed model, which the run store does not name (WISE-441 / G31 check 4). `prices.json` has a `default` row at the highest rate per token kind; `agent_usage.py` prices Auto there and flags `(Auto at the ceiling rate)` on the `--ticket` line (WISE-442; G8 in `docs/compatibility.md`).

Observed (WISE-441 Cursor trial, [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441)): a Cursor subagent with `model: inherit` under an Auto parent ran on `cursor`/`default` (CT-7 implementer and dual-review). Gantt/run paths recorded `model: default`. Mid-thread build configure is a no-op because spec and build both route to `default`. A Cursor security-review PASS was posted on CT-7 PR #13; keep approval risk tolerance strict until `readonly` MCP enforcement is proven (G4). Full table: the 2026-11-15 entry under Runs in `docs/compatibility.md`.

### Codex

Provider id: not recorded yet. `cos_models.py` has no routing for it (no role is routed). A Chief of Staff on this harness can report status and tickets but starts no child or helper (models.md § Models).

### Antigravity

Provider id: not recorded yet. `cos_models.py` has no routing for it, as for Codex.
