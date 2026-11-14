# CW-299 plan: helper session on the gantt for Linear and Jira tickets

Spec: `docs/superpowers/specs/2026-11-14-cw-299-helper-gantt-linear-jira-design.md`

## Task 1: the test

In `agent-team/scripts/dashboard/api.test.ts`, add one table-driven test, `a helper session joins its filed ticket's Todo or Backlog row on Linear and Jira`, next to `where a root checkout TICKET HELPER snapshot lands`, reusing its `helper`, `hist`, `build` helpers.

- Items come from `createTrackerLists` (`lists.ts`) fed a `tracker-lists.json` text in the tracker's shape: Linear (`identifier: 'ENG-12'`, `title`, numeric `priority`, ISO `createdAt`) and Jira (`key: 'PROJ-7'`, `fields.summary`, `fields.priority.name`, `fields.created` with a `+0000` offset). Call `want(prefix)` then `get()`.
- `buildApi` gets `repo: { url, isGithubIssues: false }`, the prefix and the items.
- Rows: Linear Backlog live, Jira Backlog live, Jira Todo live, Linear and Jira from `history[id]` only (no live snapshot), and a Linear ticket the saved lists do not hold (session nowhere).
- Assert the session id is in that row's `gantt`.
- Run: `node --test agent-team/scripts/dashboard/api.test.ts`. If a row fails, fix `api.ts` or `lists.ts` (report it).

## Task 2: docs/compatibility.md

Per the spec Design 3: Linear cell of "Ticket helper in the gantt" (Matrix 2) to `🟢 works` noting the list lag (G22); Jira to `⚪ untested: same code as Linear (G12)`; drop G23 and its references (Matrix 2 note, Matrix 1 note "(G23)"); reword the Matrix 2 note; add G24 (Jira Data Center `_` keys) after G23's slot, ticket `none yet`. Prose: no em dashes.
