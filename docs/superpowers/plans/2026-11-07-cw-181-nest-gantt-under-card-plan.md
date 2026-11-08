# CW-181 plan: nest each Gantt chart under its status card

Spec: `docs/superpowers/specs/2026-11-07-cw-181-nest-gantt-under-card-design.md`. Tests per `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: match in `api.ts`

- Export `parseWorktrees(text)`: `git worktree list --porcelain` text to `{ path, branch }[]`, skipping detached worktrees (no `branch` line).
- `buildApi` takes `worktrees` and `prefix` inputs (both default to `[]` and `null` so existing callers and tests keep working). Add `gantt?: Api['gantt']` on `StatusRow`. Match per the spec § 1 (longest worktree path equal to or parent of `cwd`; state `branch` first, then `feat/<prefix lower>-N-` fallback; only tickets with a row on the board). Matched snapshots go on `row.gantt` sorted by `updatedAt` ascending; the rest stay in top-level `gantt`.
- Test in `api.test.ts`: table covering equal cwd, cwd under worktree, nested beats root, state-branch match, pattern fallback, root on `main` unmatched, ticket not on the board unmatched, detached worktree skipped by `parseWorktrees`.

## Task 2: server

- `server.ts`: background `git -C <root> worktree list --porcelain` through `execFile` (5s timeout), cached 30s, last good list kept on failure, never awaited by `/api`. Pass `worktrees` and `prefix` (via `prefixFromProject`) into `buildApi`. Keep the change small; no new test unless `server.test.ts` breaks.

## Task 3: page

- `app.js`: `renderStatus(groups, open = new Set())` adds `<details class="chart" data-ticket=ID [open]><summary>Agents <span class="pill">n</span></summary><div class="chart-body" data-ticket=ID></div></details>` below the next line when `r.gantt` is non-empty. `draw` fills each `.chart-body` with `renderGantt(row.gantt, now)` (find rows by id from `last.status`) and `#gantt` from `last.gantt`. `poll` compares status with `gantt` stripped to session ids (so snapshot numbers don't rebuild cards), and on rebuild collects open `details.chart` ids first and passes them to `renderStatus`. Escape ids with `esc`.
- `index.html`: small CSS for `details.chart`/`summary`, nested `.session` without outer margin.
- Test in `app.test.js`: row with `gantt` gets a closed `details.chart` with the count; `open` when its id is in the set; row without `gantt` gets none.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
