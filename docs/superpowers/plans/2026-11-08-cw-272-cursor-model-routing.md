# CW-272 Cursor model routing: plan

**Spec:** `docs/superpowers/specs/2026-11-08-cw-272-cursor-model-routing-design.md` (approved at 18ced32). The spec is the source for every value and call site; this plan only orders the work and sets the checks.

Test command: `python3 -I -m pytest -q agent-team/scripts` (the suite also runs the dashboard and mod tests only when `mods/` or `scripts/dashboard/` change; this ticket touches neither).

## Task 1: Prices

- `agent-team/scripts/prices.json`: add `grok-4.7` (2, 6, read 0.50, write_1h 2, write_5m 2) and `composer-2.5` (0.50, 2.50, read 0.20, write_1h 0.50, write_5m 0.50).
- `price_fixture.json`: add both under `published`; add the sources (docs.x.ai/developers/models/grok-4.7, cursor.com/docs/models-and-pricing, read 2026-11-08) to `source`; add one hand-worked `cases` row each (dollars worked by hand).
- `test_agent_usage.py`: add a `test_ticket_line_with_cursor` row per routed model whose run gives a dollar cost, not `cost unknown`.
- Check: `test_prices.py` and `test_agent_usage.py` pass.

## Task 2: Cursor agent files, then the routing test

- `agent-team/.cursor/agents/{code-reviewer,security-reviewer}.md`: `model: grok-4.7`. `{implementer,documenter,compacter}.md`: `model: composer-2.5`. Nothing else in those files changes.
- `test_agent_files.py` `test_cursor_twin_matches_the_claude_agent`: the Cursor twin's model is the mapped one (`opus` to `grok-4.7`, `sonnet` to `composer-2.5`) in place of `inherit`.
- `AGENTS.md` § Agent config and `agent-team/docs/agents/org-chart.md` line 110: say the copies pin the matching Cursor model.
- New `agent-team/scripts/test_cursor_routing.py`, one table-driven test: collect the ids from the `model:` lines in `.cursor/agents/*.md`, the backticked ids in the § Models Cursor table of `chief-of-staff/SKILL.md`, and every `providerInstanceId: "cursor"` / `instanceId: "cursor"` model in `agent-team/.claude/skills/**/*.md`. Each must have `agent_usage.family(id)` as a key of `PRICES` and must not contain `claude`.
- Depends on Task 3 for the table; run it after Task 3.

## Task 3: chief-of-staff and the other call sites

- `chief-of-staff/SKILL.md` § Models: add the `Cursor` subsection (the spec's table, exact `target: {providerInstanceId: "cursor", model, options}` and `modelSelection: {instanceId: "cursor", ...}` forms, option names `reasoning_effort` and `fastMode` for Grok 4.7, `fastMode` for Composer 2.5), the one rule (read own provider at startup; on `cursor` every model value uses this subsection), and the CW-256 note (not yet observed; the three open questions). Backticked model ids appear in the table only as `grok-4.7` / `composer-2.5`.
- Add a short "on Cursor, § Models Cursor" pointer at each call site: SKILL.md step 2 (line ~102) and child start (~387), `startup.md` step 3 (check `composer-2.5`, fast mode off), `continuation.md` (~19), `ticket-helper.md` step 1, `rotation.md` step 2, `project-manager/reference.md` (lines ~8 and ~64). Claude Code values stay.
- SKILL.md line ~188: the `configure` line is `configure <child> build`, with the sentence from the spec saying to switch to the build-stage model for this thread's provider.
- `agent-team/scripts/cos_tick.py` line ~197: print `configure {childThreadId} build`. `test_cos_tick.py` `CONFIGURE = "configure q1 build"`.
- Role docs: `docs/agents/chief-of-staff.md` line 8 and `docs/agents/ticket-writer.md` line 7 name both models, Claude Code first.
- Check: `test_cos_tick.py`, `test_agent_files.py`, `test_call_sites.py`, then Task 2's routing test.

## Task 4: Fallbacks

- `security-review/SKILL.md` line ~25: ask for `grok-4.7` (`chief-of-staff` § Models); if the tool can't pick, the child's own model; drop "the strongest model its tool offers". `docs/agents/security-review.md` line 3: Grok 4.7 on Cursor.
- `build-from-plan/SKILL.md` (lines 27, 54), `open-pr/SKILL.md` (lines 97, 170): name the fallback by host (Sonnet or Opus on Claude Code; `composer-2.5` or `grok-4.7` on Cursor).
- `ship-loop/SKILL.md` § Models: add the Cursor models for the subagents.
- Keep each edit to one clause. These skill files are size-checked, so add no prose beyond what the spec lists.

## Task 5: Compatibility doc

- `docs/compatibility.md` G8 and the Usage and cost report row's Cursor cell, worded as in the spec § Compatibility doc.

## Task 6 (parent)

- Compaction pass, then file the CW-256-sibling follow-up ticket with `write-ticket`.
