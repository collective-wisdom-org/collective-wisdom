---
name: kickoff-feature
description: >-
  Starts a new feature with spec, ticket, git worktree, and
  implementation plan. Use for new features, new worktrees, tickets, or
  when the user asks to write a spec or plan before coding.
user-invocable: true
---

# Kickoff feature

Read **ship-loop** § Repo invariants first, then the required reading list in the repo root **`AGENTS.md`** (skim before the spec).

## Steps

1. Ticket: a task that names one has it; create none. Otherwise write it with **write-ticket** first and link the spec in its description once pushed.
2. Worktree: **using-git-worktrees** with the overrides in **ship-loop** § Repo invariants (branch pattern and `<head>`, scope, prefix). In a worktree T3 made, branch from `origin/<target>`:

   ```bash
   git fetch origin
   git switch -c <head><prefix>-N-short-title origin/<target>
   ```

   From the root checkout on the merge target branch, add a worktree instead:

   ```bash
   git fetch origin
   git worktree add .worktrees/<short-name> -b <head><prefix>-N-short-title origin/<target>
   ```

3. **brainstorming** (design gate): settle goal, scope and non-goals; write the spec without asking the user anything, listing every unspecified choice under `## Calls I made`.
4. **superpowers-project-memory**: spec path, plan path, templates. Skip its index rows: `~/.collective-wisdom/scripts/docs_index.py` generates the index.
5. Commit and push the spec, then stop at `BUILD READY` (`ship-loop` § Phases). The spec is approved per `ship-loop` § Approvals.
6. After the spec approval, **writing-plans**: a plan from the approved spec (path per **superpowers-project-memory**); don't wait for plan approval, go on to **build-from-plan**. A ticket that changes only markdown files (docs, skills, role docs) skips the plan and builds from the spec; one that changes a script, a test, `install.sh` or config writes one. Size each task's tests to `AGENTS.md` § Testing: one table-driven test per rule, none for styling or small UI interactions.

## Scope

Stay within the assigned ticket, the area boundaries in `docs/agents/project.md` § Areas and labels (if it lists any) and the role docs under `docs/agents/`.

## Do not

Commit `.env` or secrets.
