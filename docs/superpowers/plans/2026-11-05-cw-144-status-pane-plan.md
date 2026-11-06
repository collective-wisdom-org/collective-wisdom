# CW-144: status pane plan

**Spec:** [2026-11-05-cw-144-status-pane-design.md](../specs/2026-11-05-cw-144-status-pane-design.md)

Work in the worktree `.worktrees/status-pane`. Edit under `agent-team/` only. Type reference for the mod API: `grep` the file the `plugin-authoring` skill names (`types/claude-code.d.ts`); `examples/pane.tsx` there is the closest example.

## Task 0: checks that must stay green

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

## Task 1: grouping function and its test

- Create `agent-team/.claude/mods/status-pane/hooks/groups.ts` exporting `groupTickets(state)`: the groups of `chief-of-staff/status.md` § Status layout in that order, empty groups dropped, count per group, queued groups in `queue` order, row = `{ id, title, risk, next, childThreadId }`. Risk is the text after `Risk:` in the ticket's `status` (else `not rated yet`); `next` is the text before it. Any malformed input returns `[]`, never throws.
- Create `groups.test.ts` beside it: one table covering several stages and groups, queue order, empty groups dropped, a missing `childThreadId`, a `status` with no `Risk:` tail, malformed input.
- Run `claude plugin test` on the mod folder.

## Task 2: the mod

- `.claude-plugin/plugin.json` (name `status-pane`, `userConfig` options `environmentId` string and `autoOpen` boolean default false), `hooks/hooks.json` (`{ "modules": ["./register.tsx"] }`), `hooks/register.tsx`.
- `/status-pane` command opens a `Pane`; `session.start` opens it only when `autoOpen` is on.
- Every 5 seconds (`$.clock.every`) stat `.agent-team/state.json` with `$.fs`; read and parse only when `mtimeMs` changed. Missing, empty or unparsable file: keep the last good view, or show `No state yet.`
- Draw the groups as headed lists, ticket cell `CW-N title` plus a `Link` with `href` `t3-thread://v2/<environmentId>/<childThreadId>`; no link when either piece is missing.
- Under the groups, `Subagents (n)` from `$.agent.list()`, each a `Button` whose `onPress` calls `$.ui.view({ agentId })`, then a `Back to main` button calling `$.ui.view({})`.
- `claude plugin validate` and `tsc -p` on the mod folder pass.

## Task 3: install and docs

- `install.sh`: add `.claude/mods` to `shipped()` and a `sync_dir` for it beside skills and agents; check `TOUCHED`. Keep shellcheck clean.
- `agent-team/scripts/test_install.py`: one test that a fresh install and an `--update` both carry `.claude/mods/status-pane/`, following the existing tests' setup. Run `test_root_links.py` and fix any layout rule the new directory trips.
- `agent-team/docs/agents/status-pane.md`: how to turn it on, how to read the environment ID off a thread link (`t3-thread://v2/<environment id>/<thread id>`), what the pane leaves out. Plain sentences, no em dashes. Link it from `agent-team/docs/agents/README.md` if that file lists docs.

## Task 4: commit

Conventional commits (`feat:`), push `feat/cw-144-status-pane` only.
