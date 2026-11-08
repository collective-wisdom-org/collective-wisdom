# CW-178: Show Gantt charts in the dashboard only for agents on worktrees

**Status:** Draft
**Ticket:** [#178](https://github.com/collective-wisdom-org/collective-wisdom/issues/178)
**Follows:** CW-173 (#174) added the dashboard, CW-175 (#176) fit it to a side pane.

## Goal

The dashboard's Agents view lists one Gantt chart per Claude Code session that wrote a snapshot. It should list only sessions running in a worktree, so the Chief of Staff thread and other sessions in a root checkout drop out.

## Today

Facts from `main` at `d2d3bce`.

- Every session with the `agent-gantt` mod writes a snapshot with its `cwd` (`mods/agent-gantt/hooks/snapshot.ts`, `buildSnapshot`).
- `buildApi` in `agent-team/scripts/dashboard/api.ts` turns every snapshot under a day old into a chart (`cleanSnapshot`). It never looks at `cwd`.
- `repoOf` in `mods/agent-gantt/hooks/rows.ts` already knows the two worktree path shapes, each with its own regex: `/.t3/worktrees/<repo>/<name>` and `<repo>/.worktrees/<name>`.
- `rows.ts` has only a type import, so it loads in Node with no other runtime files.
- `~/.collective-wisdom` must be a link to `<clone>/agent-team` (`install.sh` refuses anything else). Node resolves the dashboard's imports from the real path, so `agent-team/scripts/dashboard/` can reach `<clone>/mods/` with a relative import.

## Builds

1. **`mods/agent-gantt/hooks/rows.ts`**: a new exported `isWorktree(cwd: string): boolean`, true when `cwd` matches either worktree shape. The two regexes move into module constants that both `isWorktree` and `repoOf` use, so the shapes are written once. `repoOf`'s results don't change.
2. **`agent-team/scripts/dashboard/api.ts`**: `cleanSnapshot` returns `null` when `isWorktree(str(s.cwd))` is false, so `api.gantt` lists only worktree sessions. It imports `isWorktree` from `../../../mods/agent-gantt/hooks/rows.ts`.
3. **Tests**:
   - `api.test.ts`: one table-driven test with three cases: a `~/.t3/worktrees/<repo>/<name>` cwd is kept, a `<repo>/.worktrees/<name>` cwd is kept, a root checkout cwd is dropped. The existing `snapshots` cases change their `cwd` from `/c` to a worktree path so they keep testing what they test now.
   - `rows.test.ts`: no new test. `repoOf`'s existing cases cover the shared regexes.

## Leaves out

- The in-session `agent-gantt` pane. It keeps showing its own session's chart wherever it runs.
- Status pane rows and the Status view.
- The snapshot files themselves: root-checkout sessions keep writing them. Only the dashboard hides them.
- A message in the Agents view when every snapshot was filtered out. The view already handles an empty list.

## Calls I made

- **The dashboard imports from `mods/`, outside `agent-team/`.** This is the first file in `agent-team/` to import from the mod. It works because `install.sh` makes `~/.collective-wisdom` a link to the clone's `agent-team/`, so `mods/` sits next to it. The other way round (the check in `agent-team/` and the mod importing it) would break the mod when it is installed with `/plugin install`, which copies only `mods/agent-gantt/`. The ticket asked to reuse `repoOf`'s check, so I did not copy it into `api.ts`.
- **Worktree means the path shape, not git.** A session counts as a worktree session when its `cwd` matches one of the two shapes `repoOf` knows. A worktree made somewhere else (for example `git worktree add ../foo`) does not count. Asking git per snapshot on every 5-second poll would cost a process per session.
- **A subfolder of a worktree counts.** The regexes match a prefix, so a session started in `<worktree>/agent-team` still shows.
- **The filter sits in `cleanSnapshot`** with the age check, so an old snapshot and a non-worktree one are dropped the same way.

## Touches

None of these: data, money, auth, user email, migrations.
