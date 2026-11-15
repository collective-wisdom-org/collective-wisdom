# CW-329 plan: keep the chief-of-staff core inside the compaction budget

Spec: [design](../specs/2026-11-14-cw-329-compaction-budget-design.md). Test command: `python3 -I -m pytest -q agent-team/scripts`.

All paths are under `agent-team/.claude/skills/chief-of-staff/` unless stated. Move text word for word; change a rule's wording only to turn its place into a pointer.

## Task 1: size and order test (write first, it fails)

In `agent-team/scripts/test_agent_files.py` add one test: in `chief-of-staff/SKILL.md`, `## Tick`, `## Child path` and `## Guardrails` appear in that order, and the byte offset of the first `## ` heading after `## Guardrails` (else the end of file) is at most 18,000. The message names the size and says to move detail into a reference file, not raise the limit. Run it: it fails at about 23,000+.

## Task 2: move text out

- `session.md` (new, with the usual "Read this when" line): `## Tools` and `## Working set` from SKILL.md, verbatim.
- `fallbacks.md` (new): three sections, `## Child read`, `## Idle check` and `## Wait check`, holding the exit-2 fallback text now in the `child-read` and `run <command>` plan-line rows and in the stuck check paragraph. Keep the `Cleanup` line wording.
- `readiness.md`: add `## Todo start` with the **Todo start** paragraph verbatim.
- Delete `## Models` from SKILL.md (`models.md` § Models holds it; keep one clause in the intro or plan-line table if a rule exists only there, e.g. exit 1 means `BLOCKED: no <role> routing`).
- In the plan-line table and Child path leave a short pointer where text left (`Exit 2: fallbacks.md § Child read`; `start-todo`: readiness.md § Todo start).

## Task 3: reorder SKILL.md

Order: frontmatter and title; re-read line; "You route work" paragraph; the `stop not-chief` / `stop paused` rules; `## Tick` (calls, exit-2 and `unsafe` rule, rerun rule, plan-line table); `## Child path`; `## Guardrails`. Then `## Turn start` (the wake list and its five bullets, the trigger table, "Not run through the tick"; `## Tick` points to it), `## When to read a reference file` (rows added: `session.md`, `fallbacks.md`; `readiness.md` gains the `start-todo` plan line; `models.md` unchanged), `## Lanes`, `## State file`, `## Lean turns`, then the end-of-file line. The Tick text that says "the table below" etc. must stay true.

## Task 4: pointers and docs

Fix every pointer to a moved section (`SKILL.md § Tools`, `§ Working set`, `§ Models`, `chief-of-staff § Models`, `§ Tick` where it means the trigger table or Todo start) in the chief-of-staff files, `project-manager`, `ship-loop`, `agent-team/docs/agents/`. `docs/compatibility.md`: G25 and check 6 say the core now fits the budget and a size test holds it, not re-run live.

## Verify

Task 1's test passes; the full suite passes; `test_section_pointers.py` passes; `git diff --stat` shows no script change besides the test.
