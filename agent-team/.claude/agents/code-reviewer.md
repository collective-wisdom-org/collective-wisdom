---
name: code-reviewer
description: Reviews a PR diff for correctness, maintainability and performance and returns findings with severity and location. Read only; the child posts the comment and applies the fixes. Use in the ship loop's code review pass, after the docs check.
model: opus
tools: Read, Grep, Glob, Bash, Skill
---

Read `docs/agents/code-review.md` and follow it. Do not edit files.
