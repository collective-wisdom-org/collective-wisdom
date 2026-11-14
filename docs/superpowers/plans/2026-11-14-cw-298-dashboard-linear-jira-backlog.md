# CW-298 plan: dashboard Todo and Backlog from Linear and Jira

Spec: `docs/superpowers/specs/2026-11-14-cw-298-dashboard-linear-jira-backlog-design.md` (approved).

## Tasks

1. **Writer `agent-team/scripts/cos_lists.py`** and `test_cos_lists.py` (one table: each accepted stdin shape saves its key and keeps the other, bad shape writes nothing and exits 2, 250 cap, non-regular file or non-directory `.agent-team` not written). It parses stdin itself (a JSON list, or an object with an `issues` or `tickets` list) and keeps entries as given, so Jira's `key` shape survives.
2. **`cos_todo.py` first pass** calls `cos_lists.save("todo", stdin text)` before it plans, ignoring any failure; add the case to `test_cos_todo.py`. Update its docstring.
3. **Reader `dashboard/lists.ts`** and `lists.test.ts` (two tests as in the spec § Tests).
4. **Server wiring** in `server.ts` and one `server.test.ts` case (a `linear` project serves the file's Todo and Backlog in `/api`).
5. **Skills and docs**: `chief-of-staff` SKILL.md (Todo start fields gain `title`; `cos_lists.py` in the script list; Backlog save after ranking and on `backlog`), `project-manager/reference.md` § Ranking child (the save step and Cleanup line), `docs/compatibility.md`, README.md § Local dashboard.
6. Run both test commands from the spec; run `compact_check.py`.
