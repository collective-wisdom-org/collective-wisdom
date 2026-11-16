# WISE-443: Set the Chief of Staff thread title on Cursor

**Status:** Shipped
**Ticket:** [#443](https://github.com/collective-wisdom-org/collective-wisdom/issues/443)
**Shipped:** in PR #469, as specified

## Goal

A Cursor Chief of Staff thread gets the `<PREFIX> - Chief of Staff` title from `project_config.py chief-title`, the same way a Claude Code thread does, and the compatibility doc says so.

## Today

Facts from main at `45ef2d7`.

- `agent-team/.claude/skills/chief-of-staff/startup.md` § Thread title has four steps. Step 4 reads "No `t3_thread_update` (Cursor): skip with no report line." So a Cursor Chief of Staff skips the rename without trying it.
- #441 settled the question. The 2026-11-15 WISE-441 run (PR #464) recorded in `docs/compatibility.md` that a Cursor Chief of Staff thread called `t3_thread_update` and renamed itself to `CT - Chief of Staff`: the Notes line "Chief of Staff thread title (G33)", the Runs entry for that thread, and G33 ("Cursor has `t3_thread_update`; WISE-441 renamed the CoS thread successfully. Ticket: none (works).").
- Matrix 1 in `docs/compatibility.md` has no "Chief of Staff thread title" row. The ticket asks to update that row's Cursor cell, so the row has to be added.
- Other mentions (`rotation.md` take-over step 3.1, `agent-team/docs/agents/chief-of-staff.md`) name no harness and stay as they are. No test reads the step text.

## Design

The tool is there, so this takes the ticket's first branch.

### 1. `startup.md` § Thread title

Delete step 4. Steps 1 to 3 then apply on every harness: a Cursor thread runs `chief-title`, renames with `t3_thread_update`, and a failed rename or exit 2 adds the Cleanup line of step 3 (`Thread title not set: ...`). A thread on a harness with no `t3_thread_update` gets that Cleanup line too, with the tool error, which is better than a silent skip.

### 2. `docs/compatibility.md`

- Matrix 1: add a row `Chief of Staff thread title` after the `Chief of Staff thread` row.
  - Claude Code: `🟢 works`.
  - Codex: `⚪ untested (G2)`.
  - Cursor: `🟢 works: WISE-441 renamed the thread to CT - Chief of Staff with t3_thread_update; since WISE-443 startup.md renames on Cursor like the other harnesses (G33)`.
  - Antigravity: `⚪ untested (G18)`.
- G33: say the tool is there (WISE-441), and that WISE-443 dropped the Cursor skip so the Chief of Staff renames on Cursor and a failed rename adds a Cleanup line. Ticket link #443.
- The Notes line "Chief of Staff thread title (G33)" gets the same WISE-443 clause.

## Leaves out

- Codex and Antigravity titles (ticket out of scope). Their new cells say only untested, with the existing gap numbers.
- No script or test change. `project_config.py chief-title` is unchanged.
- No new Cursor run. The acceptance rests on the WISE-441 run already recorded.

## Calls I made

- Matrix 1 has no thread title row today, so I add one. Its Codex and Antigravity cells are filled `untested` with the existing gaps G2 and G18 rather than left out, because a table row needs all four cells. That adds no claim about those harnesses.
- The ticket changes only markdown, so there is no plan; the build works from this spec.
- I treat the WISE-441 rename as enough proof: it is the run #441 was opened to record, and no new Cursor run is part of this ticket.
- On a harness that truly lacks `t3_thread_update`, the Chief of Staff now reports a Cleanup line instead of skipping silently. I chose that over keeping a generic skip step, since no harness the team runs is known to lack the tool.
