---
name: build-from-plan
description: >-
  Implements an approved plan from the feature worktree with scoped tests
  and verification. Use when the user says implement the plan, execute tasks,
  or build the feature.
user-invocable: true
---

# Build from plan

Before acting, read **ship-loop** § Repo invariants.

## Preconditions

1. Confirm **cwd** is the feature worktree, not root on the merge target branch.
2. Load the plan from `docs/superpowers/plans/` (path from kickoff or user). A ticket that changes only markdown files has no plan; build from the spec.
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

- Commit and push as tasks finish.
- Never push to the merge target branch. Push only this ticket's `feat/<prefix>-N-*` branch.
- No force-push to the merge target branch.

## Compaction pass

After the last task passes, run `python3 scripts/compact_check.py` and keep its totals.

- `compact: skip`: go on. Exit 2: run it once more; a second exit 2 is `BLOCKED:` (`ship-loop` § Blocked).
- `compact: run`: start the compacter (`Agent`, `subagent_type: "compacter"`, foreground; if the type isn't listed, a general Sonnet subagent told `Read docs/agents/compacter.md and follow it.`) with the base `origin/<target>` and the output.
- Then check that `git status` shows only files from the output, run the `project.md` test command, and revert any hunk that drops or changes a rule. Commit `docs: compact agent text for <PREFIX>-N` and push.

**open-pr** puts the before and after totals in the PR body (`Context size:`).

## When all tasks pass

Go straight to **open-pr** (open + feedback loop). Don't offer a choice.
