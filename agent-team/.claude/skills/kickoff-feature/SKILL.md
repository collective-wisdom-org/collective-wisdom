---
name: kickoff-feature
description: >-
  Starts a new feature with spec, Linear issue, git worktree, and
  implementation plan. Use for new features, new worktrees, Linear issues, or
  when the user asks to write a spec or plan before coding.
user-invocable: true
---

# Kickoff feature

Before acting, read **ship-loop** § Repo invariants.

Required reading: list in repo root **`AGENTS.md`** (skim before spec).

## Linear & branch

- Linear team, issue identifier prefix and project: `docs/agents/project.md` § Identity (`<TEAM>`, `<PREFIX>`).
- **One Linear issue = one branch = one PR.** Branch: `feat/<prefix>-N-short-title` (the pattern in `docs/agents/project.md` § Git and GitHub).

## Normal path

1. **brainstorming** — design gate; clarify goal, scope, non-goals.
2. **superpowers-project-memory** — spec path, plan path, index rows, templates (do not duplicate here).
3. Get user approval on the spec (or revise).
4. Write the issue with **write-ticket**; link the spec in the description.
5. Worktree — follow **using-git-worktrees**, with this repo's overrides in **ship-loop** § Repo invariants. From root on `main`:

   ```bash
   git fetch origin
   git worktree add .worktrees/<short-name> -b feat/<prefix>-N-short-title origin/main
   ```

6. **writing-plans** — plan from approved spec (path per **superpowers-project-memory**). Size each task's tests to `AGENTS.md` § Testing: one table-driven test per rule, none for styling or small UI interactions.
7. Tell user next step: approve plan → **build-from-plan** in the worktree.

## "Start now" path

When the user builds before spec approval:

1. Proceed in worktree as directed.
2. Before PR: retroactive spec per **superpowers-project-memory** § "Start now" path. As-built and index entry (`docs/superpowers/index/<prefix>-N.md`): right after PR creation per **open-pr** § Closeout docs (not before the PR exists).
3. Next feature defaults to normal path unless user says "start now" again.

## Scope

- Stay within the assigned Linear issue and the area boundaries in `docs/agents/project.md` § Areas (if it lists any) and the role docs under `docs/agents/`.

## Do not

- Commit unless the user asks.
- Expand scope beyond the Linear issue.
- Commit `.env` or secrets.

## Team mode

When the task says `TEAM MODE`, follow `ship-loop` § Team mode. Overrides:

- The Linear issue exists. Skip step 4 and don't create one.
- Create the branch in the worktree T3 made, from `origin/main`. Skip the `git worktree add` step.
- Don't ask the user to approve the spec. Put unspecified choices under `## Calls I made`.
- Commit and push the spec (the "Commit unless the user asks" rule is lifted), then stop at `SPEC READY`.
- After a relayed spec approval, write the plan with **writing-plans** and don't wait for plan approval. Go on to **build-from-plan**.
