# CW-280 plan: same-harness children

Spec: `docs/superpowers/specs/2026-11-13-cw-280-same-harness-children-design.md` (approved). Build exactly what the spec's Design sections 1 to 7 say.

## Task 1: state keys, tick check, test (scripts)

Files: `agent-team/scripts/cos_state.py`, `agent-team/scripts/cos_tick.py`, `agent-team/scripts/test_cos_tick.py`.

- `cos_state.py`: allow top-level key `chiefProvider` (`{"threadId", "provider"}`, both plain strings) and ticket field `provider` (string or null). Update the key lists and the module docstring.
- `cos_tick.py`: in `look()` (every trigger that prints a look plan, before the other lines) add `chief-provider` when `chiefProvider` is missing or its `threadId` is not this thread (then no mismatch lines), else one `harness-mismatch <ticket> child=<p> chief=<p>` line per ticket in an active or queued stage whose `provider` is set and differs. Pass both values through `safe()`. A ticket without `provider` gets no line. Update the docstring.
- `test_cos_tick.py`: one table-driven test with the five cases in spec section 6.
- Verify: `python3 -I -m pytest -q agent-team/scripts`.

## Task 2: skills and docs (markdown only)

Files: `agent-team/.claude/skills/chief-of-staff/{SKILL.md,startup.md,ticket-helper.md,rotation.md,continuation.md,state-keys.md}`, `agent-team/.claude/skills/project-manager/reference.md`, `docs/compatibility.md`.

- Spec sections 1 to 5 and 7: same-harness rule, table shape, `### Claude Code`/`### Cursor`/`### Codex`/`### Antigravity`, templates read the table, new `chief-provider` and `harness-mismatch` plan-table rows, state-keys entries, helper and PM child provider lines, compat control run entry.
- Verify: `grep -rn claudeAgent agent-team/.claude/skills` matches only inside SKILL.md § Models Claude Code; no em dashes added; `python3 -I -m pytest -q agent-team/scripts` still passes.
