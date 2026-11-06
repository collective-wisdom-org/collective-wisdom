# CW-151: ticket title in the status pane rows: plan

Spec: [2026-11-05-cw-151-status-pane-title-design.md](../specs/2026-11-05-cw-151-status-pane-title-design.md)

Work in `.worktrees/pane-title`. Edit under `agent-team/`. Test command: `python3 -I -m pytest -q agent-team/scripts` (or `uvx pytest -q agent-team/scripts`).

## Task 1: `title` in state (`agent-team/scripts/cos_state.py`)

- Add `"title"` to `TICKET`.
- `op_start`: optional `title` (add to `optional=`), must be a string when given, stored trimmed as `title` (`""` when absent).
- `set` already accepts any `TICKET` key; make it reject a non-string `title`.
- Test in `agent-team/scripts/test_cos.py`: one table-driven test: start with title, start without, `set` fills it later, a non-string title is rejected on start and on set.

Done when: the new test passes and the full suite is green.

## Task 2: Chief of Staff passes the title

- `agent-team/.claude/skills/chief-of-staff/SKILL.md`: where the skill builds the `start` op, add `title` (the ticket title it already read for the readiness check). Find the spot with `grep -n '"op": "start"\|start op\|firstTaskId' ` in the skill files.
- `agent-team/.claude/skills/chief-of-staff/state-keys.md`: document the `title` key in one line.

Done when: both files mention `title` and nothing else in them changed.

## Task 3: the pane (`agent-team/.claude/mods/status-pane/`)

- `hooks/register.tsx`: remove the `Link` thread link, the `environmentId` option read and the `Link` from the destructure. Keep `autoOpen`. The row stays `ID title | risk | next`.
- `hooks/groups.ts` and `types/index.d.ts`: remove `childThreadId` from `StatusPaneRow` and `row()`.
- `.claude-plugin/plugin.json`: remove `environmentId` from `userConfig`.
- `hooks/groups.test.ts`: update for the removed field; rows with and without a title.
- `agent-team/docs/agents/status-pane.md`: remove the `environmentId` option, the "Find the environment ID" section and the "ticket titles from the tracker" line in "What it leaves out"; say a row shows the title the Chief of Staff stored at start, and the ID alone when there is none.
- `agent-team/docs/agents/README.md`: fix any line that mentions thread links for the pane.

Done when: `grep -rn "environmentId\|childThreadId\|t3-thread" agent-team/.claude/mods/status-pane agent-team/docs/agents/status-pane.md` finds nothing, and `node --test` on `groups.test.ts` passes if the repo can run it (CW-144 ran it with `claude plugin test`; say which you used).

## Task 4: install check

Run the full suite. `agent-team/scripts/test_install.py` mentions the mod: make sure it still passes.
