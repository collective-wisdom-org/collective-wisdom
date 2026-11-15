# CW-347 plan: refresh the dashboard Todo list on a state change

Spec: `docs/superpowers/specs/2026-11-14-cw-347-todo-list-refresh-design.md` (approved). Read it first; it decides every behaviour below.

Test commands: `python3 -I -m pytest -q agent-team/scripts` (needs `uvx pytest -q agent-team/scripts` if pytest is missing) and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` (Node 24+).

## Task 1: `cos_lists.py changed`
- `agent-team/scripts/cos_lists.py`: add kind `changed` (no stdin). Sets top-level `"changed": "<UTC now>"`, keeps `todo`/`backlog`. Same folder/regular-file/temp-rename checks as `save`. Prints `lists: saved changed`; exit 2 `lists: cannot <what>`. Update the docstring. `todo`/`backlog` behaviour is unchanged (`save()` must not drop the stamp).
- `agent-team/scripts/test_cos_lists.py`: one table-driven test: `changed` writes the stamp and keeps both lists; a list save keeps the stamp; a linked file is refused.

## Task 2: dashboard server side
- `dashboard/lists.ts`: file read interval 10 s -> 1 s; expose `changed(): string | null` and `error(): string | null`; the file is read for the stamp on every tracker (add a way to `want` for GitHub that reads the stamp but keeps no lists, e.g. `want(prefix, { lists: boolean })`). Missing file is not an error; unparsable file, or a `todo`/`backlog` key that is not `{ list: [...] }`, sets `error()` (text per spec); a good read clears it. Last good lists stay.
- `dashboard/backlog.ts`: `want(cfg, changed)`. A new stamp (different from the last seen; the first stamp seen counts as seen) starts a read at once; if a read is running, run exactly one more right after it. Add `error()`: set on a failed `gh` call or non-list output (text per spec: first line of the error, control characters stripped, 120 chars), cleared on the next good read. Keep the 60 s refresh.
- `dashboard/server.ts`: read the stamp each `/api` build, pass it to `backlog.want`, return `trackerError` (from backlog on GitHub, from trackerLists on Linear/Jira) in the `/api` JSON.
- Tests: `backlog.test.ts` one table-driven test and `lists.test.ts` one, covering the spec's Tests list. Mind `server.test.ts` if it builds the API.

## Task 3: the one page line
- `git fetch origin && git rebase origin/main` first (CW-345 changed `page/app.js`).
- `dashboard/page/app.js`: `err.textContent = [last.restartError, last.trackerError].filter(Boolean).join(' ')`. No other page change, no new page test.

## Task 4: Chief of Staff files (no `SKILL.md` edit)
- `chief-of-staff/commands.md`: one new row for "mark N todo", "move N to backlog" or any request to set a ticket to Todo or Backlog, per the spec; `cancel N` row gains "then the dashboard refresh (the mark-N row)". Wording: plain, no em dashes, short.
- `chief-of-staff/session.md`: add `cos_lists.py changed` to the script list.
- Update the `cos_lists.py` mentions in `chief-of-staff/SKILL.md` only if untouched is impossible; otherwise leave it. `test_agent_files.py` must still pass (core under 18,000 bytes).
- `docs/agents/org-chart.md` line for the Chief of Staff says it writes only `tracker-lists.json` through `cos_lists.py`; that stays true, no edit.

## Verify
Run both test commands and `shellcheck` is not needed (no shell changes). Commit per task, push the branch `feat/cw-347-todo-list-refresh`.
