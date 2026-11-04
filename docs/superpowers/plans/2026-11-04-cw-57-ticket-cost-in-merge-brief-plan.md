# CW-57 plan: put the cost of each ticket in the merge brief

Spec: [2026-11-04-cw-57-ticket-cost-in-merge-brief-design.md](../specs/2026-11-04-cw-57-ticket-cost-in-merge-brief-design.md). All paths below are under `agent-team/`.

1. `scripts/agent_usage.py`: add `--ticket <PREFIX>-N`. `read_session` also returns the first and last event time and each request's billed tokens. `stage_at` takes a starting stage so a continuation child starts in the stage its task names. The no-flag report is unchanged.
2. `scripts/cos_brief.py`: `pr` reads `headRefName`, runs `agent_usage.py --ticket` for `feat/<prefix>-N-...`, and prints `cost: <line>` or `cost: unknown`. Cost never makes `pr` exit 2.
3. Tests: one table-driven `--ticket` test in `test_agent_usage.py`; one `cost:` line test in `test_cos_brief_cost.py` with the script call stubbed.
4. Docs: `approvals.md` (step 1 and a `Cost:` line in the merge block), `SKILL.md` § Report format (the `Done since last report` line and one rule), `status.md` (`$X so far` in the detail cell).
5. Verify: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
6. Open the PR, closeout docs, docs check, code review, security review, per ship-loop § Team mode.
