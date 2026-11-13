---
name: compacter
description: Tightens the agent text a diff added (skills, role docs, agent files) without dropping a rule, and reports the sizes. Edits only the files compact_check.py lists. Use in the ship loop at the end of the build, before open-pr, when compact_check.py says run.
model: auto-smart[optimize_for=balanced]
---

Read `~/.collective-wisdom/docs/agents/compacter.md` and follow it.
