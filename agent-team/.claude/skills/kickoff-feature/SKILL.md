---
name: kickoff-feature
description: >-
  Starts a new feature with spec, ticket, git worktree, and
  implementation plan. Use for new features, new worktrees, tickets, or
  when the user asks to write a spec or plan before coding.
user-invocable: true
---

# Kickoff feature

Before acting, read **ship-loop** § Repo invariants.

Required reading: list in repo root **`AGENTS.md`** (skim before spec).

## Steps

1. Ticket: if the task names a ticket, it exists; don't create one. Otherwise write the issue with **write-ticket** first, and link the spec in its description once the spec is pushed.
2. Worktree: follow **using-git-worktrees**, with this repo's overrides in **ship-loop** § Repo invariants (branch pattern, tracker scope and issue prefix are there too). `<head>` below is the first head in the `Branch pattern` row of `project.md` (`feat/` if none) unless the task names another. In a worktree T3 made, create the branch from `origin/<target>` (`<target>` is the merge target branch, the `Merge target branch` row of `project.md`, default `main`):

   ```bash
   git fetch origin
   git switch -c <head><prefix>-N-short-title origin/<target>
   ```

   From the root checkout on the merge target branch, add a worktree instead:

   ```bash
   git fetch origin
   git worktree add .worktrees/<short-name> -b <head><prefix>-N-short-title origin/<target>
   ```

3. **brainstorming**: design gate; settle goal, scope, non-goals. Write the spec without asking the user anything. List every choice the user didn't specify under a `## Calls I made` heading in the spec.
4. **superpowers-project-memory**: spec path, plan path, templates. Skip its index rows: `~/.collective-wisdom/scripts/docs_index.py` generates the index from the doc folders.
5. Commit and push the spec, then stop at `BUILD READY` (`ship-loop` § Phases). The spec is approved per `ship-loop` § Approvals.
6. After the spec approval, **writing-plans**: plan from the approved spec (path per **superpowers-project-memory**). Don't wait for plan approval; go on to **build-from-plan**. Skip the plan when the ticket changes only markdown files (docs, skills, role docs): the spec is enough, so build from it. A ticket that changes a script, a test, `install.sh` or config writes a plan. Size each task's tests to `AGENTS.md` § Testing: one table-driven test per rule, none for styling or small UI interactions.

## Scope

- Stay within the assigned ticket and the area boundaries in `docs/agents/project.md` § Areas and labels (if it lists any) and the role docs under `docs/agents/`.

## Do not

- Commit `.env` or secrets.
