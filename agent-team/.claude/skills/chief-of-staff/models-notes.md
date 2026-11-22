# Models: notes

Read this for the Cursor, Codex or Antigravity notes. Why each role runs on its model: the `cos_models.py` docstring.

### Claude Code

Fable 5.1 and Haiku 5.5 are not used: they are not part of the default setup.

### Cursor

No Cursor run starts on a Claude model, Grok, Composer or Gemini; the team routes only to Auto (CW-275: the user's Cursor cannot pick models). Auto is the model `default` with no options, for every role. A subagent runs on `model: inherit` in its `.cursor/agents` file, so it takes its parent thread's model, which is Auto. The context window stays at Cursor's default.

Auto bills at the list price of the routed model, which the run store does not name (WISE-441 / G31 check 4). `prices.json` has a `default` row at the highest rate per token kind; `agent_usage.py` prices Auto there and flags `(Auto at the ceiling rate)` on the `--ticket` line (WISE-442; G8 in `docs/compatibility.md`).

Mid-thread build configure is a no-op because spec and build both route to `default`. Keep approval risk tolerance strict until `readonly` MCP enforcement is proven (G4). The WISE-441 trial ([#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441)) results: the 2026-11-15 entry under Runs in `docs/compatibility.md`.

### Codex and Antigravity

Provider id not recorded yet. `cos_models.py` has no routing for either (no role is routed). A Chief of Staff there reports status and tickets but starts no child or helper (models.md § Models).
