# CW-404 plan: rename the ticket prefix from CW to WISE

**Spec:** [spec](../specs/2026-11-15-cw-404-rename-prefix-wise-design.md)
**Ticket:** [#404](https://github.com/collective-wisdom-org/collective-wisdom/issues/404)

Two tasks, run in order. Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: Python side

Files: `agent-team/scripts/project_config.py`, `cos_untracked_check.py`, `pm_hygiene.py`, `agent_usage.py`, `test_prefix_free.py` (new), `agent-team/templates/project.md`.

1. `project_config.py`: add `retired_prefixes()`, `prefixes()`, `ticket_id(number)`, `ticket_number(tid)`, `branch_ticket_re()`; `ticket_re()` matches every prefix (escaped, longest first). `chief_thread_title()` stays current-prefix. Row `Retired issue prefixes`: one backticked token of `PREFIX<N` pairs, oldest first; missing, `none` or empty gives (); a set but bad row (bad prefix, equals current, duplicate, non-rising numbers) raises `SystemExit("project.md: 'Retired issue prefixes' row ...")`.
2. `cos_untracked_check.py`: `prs_by_ticket` uses `branch_ticket_re()` and `ticket_id(number)`; the issue loop uses `ticket_id(issue["number"])`; `known` also counts tickets whose issue number is in state under any prefix.
3. `pm_hygiene.py`: `ticket_id` uses `project_config.ticket_id(number)`; `ticket_of` reads branches with `branch_ticket_re()` and titles with `ticket_re()` and returns `ticket_id(number)`.
4. `agent_usage.py`: error text drops the literal `CW-57`, reads the current prefix.
5. Template row `Retired issue prefixes` = `none`, with the GitHub-only note.
6. Tests: `test_prefix_free.py` with the two tests in the spec's "Hardcoded-prefix test" (the `ZZ`/`YY<10` fixture table, and the source scan). Existing tests stay green.

Verify: `python3 -I -m pytest -q agent-team/scripts`.

## Task 2: Dashboard and repo files

Files: `dashboard/titles.ts`, `merged.ts`, `api.ts`, `lists.ts`, `backlog.ts`, `server.ts`, `page/app.js` (the `CW-220` note becomes `the token rate fix`), one table row in the existing dashboard tests, `docs/agents/project.md`, `CONTRIBUTING.md`.

1. `titles.ts`: `retiredFromProject(markdown)` (bad row gives `[]`) and `idForNumber(number, prefix, retired)`. Thread the retired list through `merged.ts`, `api.ts` (`ticketOf`, `cleanTeamSnapshot`), `lists.ts`, `backlog.ts`, `server.ts`.
2. `project.md`: prefix `WISE`, new row `Retired issue prefixes` = `CW<CUTOVER`, Branch pattern note `<prefix>` is `wise`, Repo invariants bullet. `CONTRIBUTING.md` line 4.
3. `CUTOVER` is set at the final push (spec § The project.md row).

Verify: the Node command in `AGENTS.md`, plus the Python suite.
