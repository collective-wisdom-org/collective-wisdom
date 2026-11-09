# CW-257 plan: Cursor sessions in the usage and cost report

Spec: [2026-11-08-cw-257-cursor-usage-report-design.md](../specs/2026-11-08-cw-257-cursor-usage-report-design.md). Build exactly that.

## Task 1: `agent_usage.py`

- Add `--cursor-projects DIR` (default `~/.cursor/projects`), `read_cursor(proj)` (spec § 1: read-only SQLite URI, skip and warn on an unreadable store, skip runs with no `usage_json`), Cursor pricing (spec § 1 list), branch resolution (spec § 2: `Branch: feat/...` line of the first user message, else `git -C <workspace_ref> branch --show-current`), `<user_query>` unwrapping, stage split by turn number.
- `ticket_line`: spec § 3 (summed cost, `Cursor $Y` part, share on the Claude part only, `cost unknown (no price for <models>; $X priced)` form, exit 2 only when neither source ran the ticket).
- Window report: spec § 4.
- Update the module docstring.

## Task 2: tests (`test_agent_usage.py`)

Per spec § Tests: one table-driven `--ticket` test with a fixture builder that writes `index.db` (`agents`, `runs` with only the columns read) and a transcript, plus one stage-split case. Hand-computed dollars. Keep test lines at or under feature lines.

## Task 3: callers

- `no_hands.py`: the stop line is `no-hands: stop cost unknown (<PREFIX>-N)` (first ticket in run order with an unknown cost); update its docstring, `test_no_hands.py`, and `chief-of-staff/no-hands.md` where it quotes the line.
- `chief-of-staff/status.md` and `chief-of-staff/SKILL.md` § MERGED: show `cost unknown` when the usage line starts with it.
- `cos_brief.py`: no code change.

## Task 4: docs

`docs/compatibility.md` (Cursor cell, No Hands note, G8) and `README.md` if it says Claude Code only, per spec § Docs.

## Verify

`python3 -I -m pytest -q agent-team/scripts` passes (use `uvx pytest -q agent-team/scripts` if pytest is missing). Also run `agent_usage.py --ticket CW-257` and the window report against the real `~/.cursor/projects` as a smoke check, and report the output.
