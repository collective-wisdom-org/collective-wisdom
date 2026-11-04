# Child thread link in the status table: Implementation Plan (CW-49)

**Spec:** [2026-11-03-cw-49-child-link-in-status-design.md](../specs/2026-11-03-cw-49-child-link-in-status-design.md)

No code and no tests (prose only, `AGENTS.md` § Testing). Edit under `agent-team/` only.

## Task 1: Status layout in the skill

File: `agent-team/.claude/skills/chief-of-staff/SKILL.md`, § Report format "Status layout".

1. In each of the five example rows, remove the trailing ` <thread link>` from the Next cell and add `<br><thread link>` right after the title in the Ticket cell.
2. Add a rule to the list under the example: the Ticket cell is `**<PREFIX>-N** title`, then `<br>` and the link to the ticket's child thread (`childThreadId` in state). A row with no `childThreadId` (or a null one) has no `<br>` and no link. The link is never repeated in Next.
3. In the `where's <PREFIX>-N?` rule, say it uses the same layout "with the thread link under the ticket".
4. Change nothing else, including other sections' `<thread link>` uses.

## Task 2: Role doc

File: `agent-team/docs/agents/chief-of-staff.md` line 20: after "answers `status` in the grouped table layout" add ", with each ticket's child thread link under its ID and title" (keep the parenthetical reference).

## Verify

- `grep -n "thread link" agent-team/.claude/skills/chief-of-staff/SKILL.md` shows no Next cell in the Status layout ending with `<thread link>`.
- `python3 -I -m pytest -q agent-team/scripts` passes.
- Render one example row: `./scripts/gh.sh api markdown -f mode=gfm -f text="$(…)"` and confirm the `<br>` is in the cell.
