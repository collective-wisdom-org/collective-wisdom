# CW-205 plan: read the tracker row in the dashboard

Spec: `docs/superpowers/specs/2026-11-08-cw-205-dashboard-tracker-row-design.md`

## Task 1: parse the Tracker row (one task)

1. In `agent-team/scripts/dashboard/api.ts`, `repoUrlFromProject`: replace `markdown.includes('Tickets are GitHub issues')` with a helper that scans table lines (start with `|` after leading spaces; cells split on `|`, trimmed). The first row whose first cell is `Tracker` or starts with `Tracker (` decides: first backticked token in the second cell, lowercased, equals `github`. No row or no token is false.
2. In `api.test.ts`, extend the `repoUrlFromProject` test with one table-driven block (a `Repo` row in every case): `github` row true; `linear` row false; no Tracker row false; `linear` row plus the text "Tickets are GitHub issues" false. Keep the existing assertions.
3. Verify: `node --test agent-team/scripts/dashboard/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
