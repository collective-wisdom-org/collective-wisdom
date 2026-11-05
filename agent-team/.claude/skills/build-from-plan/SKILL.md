---
name: build-from-plan
description: >-
  Implements an approved plan from the feature worktree with scoped tests
  and verification. Use when the user says implement the plan, execute tasks,
  yes after plan approval, or build the feature.
user-invocable: true
---

# Build from plan

Before acting, read **ship-loop** § Repo invariants.

## Preconditions

1. Confirm **cwd** is the feature worktree, not root on the merge target branch.
2. Load the plan from `docs/superpowers/plans/` (path from kickoff or user).
3. Stay within `AGENTS.md` scope.

## Execution

Read and follow one of:

- **subagent-driven-development** — when plan tasks are independent.
- **executing-plans** — otherwise.

If **planner-delegates** applies: parent plans and delegates; **implementer** subagent edits files and runs verification. Start it with the `Agent` tool and `subagent_type: "implementer"`. If that type isn't listed (the session started before `.claude/agents/implementer.md` existed), start a general Sonnet subagent with the prompt `Read docs/agents/implementer.md and follow it.` plus the task.

Follow plan tasks in order; use plan file paths and acceptance criteria.

**verification-before-completion** before claiming any task done: run the plan's command and show output.

## Testing (prefer plan Task 0)

What to test, and how much: `AGENTS.md` § Testing. When a plan lists more tests than that allows, merge or drop the extras and say so.

| Area | Command pattern |
|------|-----------------|
| Plan Task 0 | Use exactly what the plan specifies |
| Everything else | The test, lint and typecheck commands in `docs/agents/project.md` § Commands, scoped to touched paths when the tool allows |
| Guards | Follow `docs/agents/project.md` § Commands (Test database) and § Repo invariants (local data directories, docker rules). Never test or migrate against the dev database |

## Git

- **Do not commit** unless the user explicitly asks.
- No force-push to the merge target branch.

## When all tasks pass

Read and follow **finishing-a-development-branch**, or prompt: *"make a pr"* → **open-pr** (open + feedback loop).

## Team mode

When the task says `TEAM MODE`, follow `ship-loop` § Team mode. Overrides:

- Commit and push as tasks finish. The "Do not commit unless the user asks" rule is lifted. Never push to the merge target branch. Push only this ticket's `feat/<prefix>-N-*` branch.
- Don't offer a choice at the end. Go straight to **open-pr**.
