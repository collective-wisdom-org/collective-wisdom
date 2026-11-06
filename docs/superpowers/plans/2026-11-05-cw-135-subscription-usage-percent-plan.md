# CW-135 plan: subscription share next to ticket cost

Spec: [design](../specs/2026-11-05-cw-135-subscription-usage-percent-design.md). All shared edits go under `agent-team/`.

## Tasks

1. `agent-team/scripts/project_config.py`: add `subscription_usage(provider)`. It reads the row whose Key starts with `<provider> subscription API-equivalent usage` and returns a float when the first backticked token parses as a positive finite number, else None.
2. `agent-team/scripts/agent_usage.py`: `ticket_line(projects, ticket, usage=None)`. With a usage figure the cost part reads `cost $X API-equivalent (P% of the subscription), ...`. P has two decimals; a positive cost under 0.01% prints `<0.01%`. `main()` passes `project_config.subscription_usage("Claude")`; any failure reads as unset. With usage None the line is unchanged.
3. `docs/agents/project.md` (value `12000`) and `agent-team/templates/project.md` (value `none` plus a short note): new Identity row `Claude subscription API-equivalent usage (dollars)` under `Approval risk tolerance`.
4. Docs: `chief-of-staff/approvals.md` `Cost:` example and `chief-of-staff/SKILL.md` § Report format `Done since last report` example and the `MERGED #N` sentence show the share when the line has one.
5. Test: extend `test_agent_usage.py` with one table-driven test (usage 12000 with $14.20 gives `0.12%`; unset, `0`, `-5`, `abc` give today's line; a $0.50 ticket gives `<0.01%`), driving the config read through `PROJECT_MD`.

## Verify

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
