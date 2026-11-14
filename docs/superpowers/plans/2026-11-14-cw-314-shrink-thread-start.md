# CW-314 plan: shrink the Chief of Staff thread start

Spec: `docs/superpowers/specs/2026-11-14-cw-314-shrink-thread-start-design.md` (approved). Text moves as is; only pointers and the listed additions change. Test budget: `AGENTS.md` § Testing.

## Task 1: cos_models.py
Add `agent-team/scripts/cos_models.py` per spec § 3: one dict per provider (`claudeAgent`, `cursor`) holding exactly the values in `SKILL.md` § Models tables and `Values` lines; roles `chief`, `ticket-helper`, `pm`, `spec`, `build`, `implementer`, `documenter`, `compacter`, `code-review`, `security-review`. Output `target: {...}` and `modelSelection: {...}` compact JSON for thread roles, `pinned: <model: line> in <agent file>` for subagent roles. Exit 0 / 1 (`cos_models: no <role> routing for <provider>`) / 2 usage. Docstring has the one-line Why per role. Add `test_cos_models.py` (one table-driven test, a row per provider and role, plus an unknown-provider row). Change `test_cursor_routing.py` to read Cursor models from the `cos_models.py` dict instead of the `### Cursor` table.
Verify: `python3 -I -m pytest -q agent-team/scripts/test_cos_models.py agent-team/scripts/test_cursor_routing.py`

## Task 2: split SKILL.md
Create the seven reference files from spec § 2 in `agent-team/.claude/skills/chief-of-staff/` (`commands.md`, `send-or-queue.md`, `report-format.md`, `readiness.md`, `models.md`, `rate-limit.md`, `sweep.md`), moving section text unchanged under the same headings. `models.md` holds the § Models rule, How a child changes model, the `t3_thread_configure` rule, Why, and the Cursor, Codex and Antigravity notes, with the tables replaced by a pointer to `cos_models.py`. Delete the moved sections and § Rotation check from `SKILL.md`; add the short § Models stub; add the new rows to § When to read a reference file; apply the § Guardrails, § Tick and § Lean turns additions from spec § 1. Fix the `cos_rotation_check.py` mention in § Tools.
Verify: `python3 -I -m pytest -q agent-team/scripts/test_section_pointers.py` (expected to fail on pointers until Task 3)

## Task 3: pointers and rotation.md
Point every pointer to a moved heading at its new file (spec § 4), in the skills, role docs, `docs/agents/`, templates and scripts' docstrings or plan lines that name them. Remove the 90k Cleanup sentence from `rotation.md` § Thread rotation (spec § 5).
Verify: `python3 -I -m pytest -q agent-team/scripts`

## Task 4: measurement
Record `wc -c` of `SKILL.md` plus the reference files a take-over reads, before (`main`) and after, for the PR body.
