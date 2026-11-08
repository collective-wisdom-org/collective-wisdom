# CW-177 plan: rename awaiting-spec and SPEC READY

Spec: `docs/superpowers/specs/2026-11-08-cw-177-rename-awaiting-spec-design.md` (approved).

## Task 1: scripts and status pane

- `cos_state.py`: rename in `STAGES`, `STAMPED`, docstring, `show` summary. In `load()`, after parsing, set `stage` to `awaiting-build` for each ticket in `state["tickets"]` (a dict of dicts) whose stage is `awaiting-spec`. Keep the old name only there.
- `approval_policy.py`: check, message and docstring use `awaiting-build`.
- `groups.ts` and its test: stage `awaiting-build`.
- `cos_ready_check.py`: docstring and `--help` say `BUILD READY`.
- Tests: switch fixtures in `test_cos.py`, `test_approval_policy.py` (also `Spec ready.` to `Build ready.`), `test_cos_handoff.py`. Add one table-driven test in `test_cos.py`: a state file with tickets in `awaiting-spec` and `awaiting-build` shows both as `awaiting-build`, an `apply` saves `awaiting-build`, and `lastSeenAt` is unchanged.
- Verify: `python3 -I -m pytest -q agent-team/scripts`; `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the status-pane tests under `agent-team/.claude/mods/status-pane`.

## Task 2: skills and role docs

Rename `awaiting-spec` to `awaiting-build`, `SPEC READY` to `BUILD READY`, `spec ready` (report wording, slot reasons, request line) to `build ready`, in `agent-team/` skills and `agent-team/docs/agents/org-chart.md`. Leave `Spec ready`-free prose like "Spec lane" alone. Add the old-marker sentence (a last message ending in the old `SPEC READY` counts as `BUILD READY`) in `chief-of-staff/SKILL.md` § Full pass step 2, `startup.md` state rebuild, and `ship-loop/SKILL.md` § Approvals. Verify with the two greps in the spec's Acceptance section.
