---
name: compacter
description: Tightens the agent text a diff added (skills, role docs, agent files) without dropping a rule, and reports the sizes. Edits only the files compact_check.py lists. Use in the ship loop at the end of the build, before open-pr, when compact_check.py says run.
model: sonnet
tools: Read, Edit, Grep, Glob, Bash
---

Read `docs/agents/compacter.md` and follow it.
