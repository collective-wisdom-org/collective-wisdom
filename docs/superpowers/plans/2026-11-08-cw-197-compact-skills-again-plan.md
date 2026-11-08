# CW-197 plan: compact the skills and role docs again, move more logic into scripts

Spec: `docs/superpowers/specs/2026-11-08-cw-197-compact-skills-again-design.md` (approved at 67a3811). Tests per `AGENTS.md` § Testing: one table-driven test per new script, test lines no more than feature lines.

CW-199 (docs check once) edits neighbouring sections of `open-pr`, `ship-loop` and `org-chart.md`; leave the sections the spec lists alone and rebase onto it if it merges first.

## Task 1: three scripts and their tests

`agent-team/scripts/cos_route.py`, `cos_restart.py`, `cos_todo.py` with `test_cos_route.py`, `test_cos_restart.py`, `test_cos_todo.py`, as the spec's design §§ 1 to 3 and § Tests say. Read `cos_tick.py`, `cos_state.py`, `cos_brief.py` and `test_cos_tick.py` for the style first. Each docstring holds the flags, output lines and exit codes. Mirror the new scripts wherever the other `cos_*.py` scripts are listed (`test_call_sites.py`, `test_agent_files.py`, docs).

## Task 2: the nothing-lost inventory (before any cut)

`docs/superpowers/as-built/2026-11-08-cw-197-compact-skills-again-as-built.md`, section `## Inventory before`: every approval gate, merge gate, repo invariant, `cos_state.py` op and Chief of Staff user command, each with the file and section that states it. Commit before Task 3 starts.

## Task 3: cuts, in three disjoint file groups

Run after Tasks 1 and 2. Spec §§ 4 to 6 and the size targets.

- A: `chief-of-staff/SKILL.md` and its siblings (`approvals.md`, `rotation.md`, `startup.md`, `state-keys.md`, `ticket-helper.md`, new `review.md` and `adopt.md`, § When to read a reference file), switching § Send or queue, § Child path stuck check and § Tick Todo start to the new scripts.
- B: `ship-loop/SKILL.md` (and new `reference.md` for § Running one phase by hand), `open-pr/SKILL.md`, `merge-pr/SKILL.md`.
- C: `project-manager/SKILL.md`, `docs/agents/chief-of-staff.md`, `docs/agents/org-chart.md`, other role docs.

Every moved or cut rule keeps one owner with a `§` pointer; no heading another file or script names is renamed. `test_section_pointers.py`, `test_call_sites.py`, `test_agent_files.py` must pass.

## Task 4: close out

As-built `## Inventory after` (where each entry is now), `## Differs from the spec`, size table; run `compact_check.py` and the full test and lint commands; compaction pass per `build-from-plan`.
