# CW-135: Show the share of a subscription used next to the dollar cost of a ticket

**Ticket:** [CW-135](https://github.com/collective-wisdom-org/collective-wisdom/issues/135)
**Status:** Draft
**Related:** #96, #57

## Goal

A ticket's cost line says what share of the Claude subscription it used, next to the dollar figure, so `$14.20` reads as `0.12% of the subscription`. The share appears only when the subscription's API-equivalent usage is typed into `project.md`.

## Today

Facts from `main` at `ef4770d`, checked 2026-11-05.

- `agent-team/scripts/agent_usage.py` `ticket_line()` returns `cost $X API-equivalent, N.NM tokens, spec $a / build $b / merge $c, R child runs, wall Hh MMm` for `--ticket <PREFIX>-N`. It prices Claude Code transcripts only.
- `agent-team/scripts/cos_brief.py` `cost_line()` runs `agent_usage.py --ticket` and prints `cost: <that line>`. `chief-of-staff/approvals.md` copies it from the first `$` into the merge brief's `Cost:` line.
- `chief-of-staff/SKILL.md` § Report format shows `Done since last report` as `- <PREFIX>-190 merged (#178), cost $14.20 (spec $2.10 / build $11.66 / merge $0.44)`, and says to run `agent_usage.py --ticket` fresh on `MERGED #N`.
- `agent-team/scripts/project_config.py` `value(key_prefix)` returns the first backticked token in a `project.md` Value cell, or None. `agent_usage.py` does not import it yet.
- No `project.md` row holds a subscription's usage. `agent-team/templates/project.md` seeds apps.
- `test_agent_usage.py` has a table-driven `test_ticket_line`.

## Design

### The setting

One new row in the `## Identity` table of `docs/agents/project.md` and of `agent-team/templates/project.md`, under `Approval risk tolerance`:

| Key | Value |
|---|---|
| Claude subscription API-equivalent usage (dollars) | `12000` here. In the template: `none`, with a note: the API-equivalent dollars the Claude plan shows; ticket costs then show a share of it |

The key names the provider. A later provider gets its own row (`Codex subscription ...`) when a script can price its usage. This ticket adds no row for any other provider.

`project_config.py` gets one helper, `subscription_usage(provider)`: the row's value as a float when it parses as a positive finite number, else None. Unset, `none`, `0`, a negative, `12,000` or text all read as None.

### The share in `--ticket`

`ticket_line()` takes the usage figure (None by default). When it is set, the cost part becomes `cost $14.20 API-equivalent (0.12% of the subscription), ...`; the rest of the line is unchanged. When it is None, the line is byte for byte what it is today.

Rounding: two decimal places. A cost above zero that rounds below `0.01%` prints `<0.01%`. A share of 100% or more prints as computed (e.g. `104.17%`); no cap.

`main()` reads the figure with `project_config.subscription_usage("Claude")` and passes it in. A failed read of `project.md` reads as unset, so `--ticket` never fails because of this row.

### Downstream

No code change in `cos_brief.py`: it copies the `--ticket` line, so the merge brief's `Cost:` line carries the share. Doc edits only:

- `chief-of-staff/approvals.md`: the `Cost:` example shows the share.
- `chief-of-staff/SKILL.md` § Report format: the `Done since last report` example becomes `cost $14.20 (0.12% of the subscription; spec $2.10 / build $11.66 / merge $0.44)`, and the `MERGED #N` sentence says to copy the share when the line has one.

### Tests

One table-driven test of the share in `test_agent_usage.py`: usage `12000` with a $14.20 ticket gives `0.12%`; unset, `0`, `-5` and `abc` give today's line; a $0.50 ticket gives `<0.01%`. It drives `ticket_line()` through `PROJECT_MD` pointed at a temp file, so it covers the config read too.

## Out of scope

- Reading the usage figure from a provider or the Claude app.
- Pricing Codex or other non-Claude usage.
- The default report totals of `agent_usage.py`, and the Gantt and cost pane (#96).

## Approval note

This spec edits `docs/agents/project.md`, `agent-team/templates/project.md` and `agent-team/scripts/`, all on the approval path. It can't be auto-approved; the tolerance here is `strict` anyway.

## Calls I made

- **Small shares print `<0.01%`**, not `0.00%` or more decimals. Most tickets cost $5 to $50, which is 0.04% to 0.42% of $12,000; two decimals read well there.
- **The figure is treated as one fixed number.** The ticket leaves the period open (month, billing cycle, all time). The wording is `of the subscription`, not `of this month`.
- **Only a Claude row, no empty rows for other providers.** The key names the provider so a Codex row can be added when its usage is readable.
- **`12,000` with a comma reads as unset**, like any other non-number. The row is typed as `12000`.
- **No cap at 100%.** A share over 100% means the figure is stale, and showing it says so.
- **The share sits inside the parentheses in `Done since last report`**, before the stage split, to keep that line short.
- **The row goes in the Identity table**, next to the approval settings, since there is no cost table.
