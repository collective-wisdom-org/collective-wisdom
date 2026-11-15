# CW-380 plan: Chief of Staff thread title

Spec: [design](../specs/2026-11-15-cw-380-chief-thread-title-design.md)

1. `agent-team/scripts/project_config.py`: add `chief_thread_title()` and a `chief-title` CLI command; update the usage line.
2. `agent-team/scripts/test_project_config.py`: one table-driven CLI test (`CW`, `GUY`, `GORP` print the title; missing row, `TODO(...)`, lower-case `cw` exit 2 with nothing on stdout).
3. `agent-team/.claude/skills/chief-of-staff/startup.md`: add `## Thread title`; call it from Setup step 4 right after storing `chiefThreadId`.
4. `agent-team/.claude/skills/chief-of-staff/rotation.md`: take-over step 3.1 runs clean-up, then § Thread title, then the dashboard step.

Verify: `python3 -I -m pytest -q agent-team/scripts`.
