---
name: build-from-plan
description: >-
  Implements an approved plan from the feature worktree with scoped tests
  and verification. Use when the user says implement the plan, execute tasks,
  or build the feature.
user-invocable: true
---

# Build from plan

Read **ship-loop** § Repo invariants first.

## Preconditions

1. **cwd** is the feature worktree, not the root on the merge target branch.
2. Load the plan from `docs/superpowers/plans/` (path from kickoff or the user). A ticket that changes only markdown files has no plan: build from the spec.
3. Stay within `AGENTS.md` scope.

## Execution

Follow **subagent-driven-development** when plan tasks are independent, else **executing-plans**. Under **planner-delegates** the parent plans and the `implementer` subagent (`subagent_type: "implementer"`; fallback `ship-loop` § Models) edits files and runs verification. Do plan tasks in order, by their file paths and acceptance criteria. **verification-before-completion** before calling a task done: run the plan's command and show its output.

## Testing (prefer plan Task 0)

What and how much to test: `AGENTS.md` § Testing. Where the plan lists more, merge or drop the extras and say so.

| Area | Command pattern |
|------|-----------------|
| Plan Task 0 | Use exactly what the plan specifies |
| Everything else | The test, lint and typecheck commands in `docs/agents/project.md` § Commands, scoped to touched paths when the tool allows |
| Guards | `project.md` § Commands (Test database) and § Repo invariants (data directories, docker rules). Never test or migrate against the dev database |

## Git

Commit and push as tasks finish. Push only this ticket's own branch (the one the task names), never the merge target branch; no force-push to it.

## Compaction pass

After the last task passes, run `python3 ~/.collective-wisdom/scripts/compact_check.py` and keep its totals for **open-pr** (after a compacter run, from a re-run once its edits are committed).

- `compact: skip`: go on. Exit 2: run it once more; a second exit 2 is `BLOCKED:` (`ship-loop` § Blocked).
- `compact: run`: start the compacter (`Agent`, `subagent_type: "compacter"`; fallback `ship-loop` § Models) with the base `origin/<target>` and the script's output. Then check `git status` lists only files from that output, run the `project.md` test command, and revert any hunk that drops or changes a rule. Commit `docs: compact agent text for <PREFIX>-N` and push.

## When all tasks pass

Go straight to **open-pr** (open + feedback loop). Don't offer a choice.
