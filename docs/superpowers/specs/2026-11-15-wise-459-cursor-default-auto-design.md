# WISE-459: Route Cursor through default Auto for every role

**Status:** Shipped
**Ticket:** [#459](https://github.com/collective-wisdom-org/collective-wisdom/issues/459)
**Shipped:** in PR #460, with differences: [as-built](../as-built/2026-11-15-wise-459-cursor-default-auto-as-built.md)

## Goal

Every Cursor role runs on Cursor's default Auto: the `default` model, labelled "Auto" in the provider's model list, with no `optimize_for` option. The two Auto tiers (Intelligence and Fast) go away everywhere the team routes or describes Cursor.

## Today

Facts from main at `5d692fb`.

- `agent-team/scripts/cos_models.py` builds `MODELS["cursor"]` from `_auto(optimize_for)`, which returns `{"model": "auto-smart", "options": {"optimize_for": ...}}`: `intelligence` for the ticket helper and spec, `balanced` for chief, pm and build. The five `pinned` entries name `auto-smart[optimize_for=intelligence]` for the two reviewers and `auto-smart[optimize_for=balanced]` for the rest. The docstring says "Cursor routes only to Auto (auto-smart): intelligence where Claude Code uses Opus, balanced elsewhere."
- `main` prints each row as JSON, so a row with no `options` key prints no options.
- `agent-team/.cursor/agents/*.md` carry the same `auto-smart[...]` values in `model:`. `code-reviewer`, `security-reviewer` and `documenter` set `readonly: true`.
- Tests that read these values: `test_agent_files.py` (`CURSOR_MODEL` maps `opus` and `sonnet` to the two tiers, and checks `readonly` against the Claude copy's tools), `test_cos_models.py` (the `auto()` helper and the Cursor rows of `SHEET`), `test_cursor_routing.py` (`UNPRICED = "auto-smart"`, and a check that the collection found `auto-smart`).
- `agent_usage.family("default")` and `family("inherit")` are both `None`, like `family("auto-smart")`: neither has a price row.
- Cursor's subagent doc (cursor.com/docs/context/subagents) says `model` is "`inherit` or a specific model ID", default `inherit`, which "uses the same model as the parent agent". It does not list `default` or `auto` as frontmatter values, and says "the model picker, including Auto, applies to the parent agent".
- Prose naming the tiers or `auto-smart`: `chief-of-staff/models.md` § Cursor, `chief-of-staff/startup.md` step 3 ("no `optimize_for` option set counts as balanced"), `ship-loop/SKILL.md` § Models, `open-pr/SKILL.md` (code review model), `build-from-plan/SKILL.md` (compacter fallback), `security-review/SKILL.md`, `agent-team/docs/agents/{chief-of-staff,ticket-writer,security-review,org-chart}.md`, `AGENTS.md` § Agent config, `agent-team/templates/AGENTS.md`, and `docs/compatibility.md` (Usage and cost report row, the No Hands note, G8).

## Design

### 1. Routing in `cos_models.py`

- Replace `_auto(optimize_for)` with a constant `AUTO = {"model": "default"}` and use it for all five thread roles. No `options` key, so `target` and `modelSelection` print `{"providerInstanceId":"cursor","model":"default"}` and `{"instanceId":"cursor","model":"default"}`.
- The five Cursor `pinned` entries become `model: inherit in .cursor/agents/<file>`.
- Docstring line: "Cursor routes every role to default Auto (`default`, no options); its subagents inherit the parent's model."

### 2. Cursor agent files

All five `agent-team/.cursor/agents/*.md` get `model: inherit`. `readonly: true` stays where it is. A subagent then runs on its parent thread's model, which is Auto for every Cursor role after §1.

### 3. Tests

- `test_agent_files.py`: the Cursor copy's `model` must be `inherit` for every agent (replaces `CURSOR_MODEL`). The `readonly` check is unchanged. A file that pins `auto-smart[...]` or any `optimize_for` fails it.
- `test_cos_models.py`: `auto()` takes only the key and returns the `default` JSON with no options; the Cursor rows of `SHEET` use it, and the Cursor pins expect `inherit`.
- `test_cursor_routing.py`: `UNPRICED = "default"`. `inherit` is dropped from the collected ids (it names no model; the parent's route is collected from `cos_models.py`). The collection check expects `default`. A role routed back to `auto-smart` then fails the priced check, since `auto-smart` has no price and is no longer the exception.

### 4. Prose

- `models.md` § Cursor: one Auto model, `default` with no options, for every role and (through `inherit`) every subagent. Drop the Intelligence and Fast tiers and the "no `optimize_for` counts as balanced" sentence. The cost paragraph names `default` instead of `auto-smart`. The "Not yet observed" paragraph keeps its open checks, rewritten: whether a subagent with `model: inherit` under an Auto parent runs on Auto, and what the run store records for an Auto run. The strict-tolerance advice for a Cursor Chief of Staff stays.
- `startup.md` step 3: compare the model with the `chief` role; drop the `optimize_for` clause.
- `AGENTS.md` § Agent config, `templates/AGENTS.md` and `org-chart.md`: the Cursor copies set `model: inherit` (they run on the parent thread's Auto) instead of mapping `opus` and `sonnet` to two tiers.
- "Auto Intelligence" and "Auto Fast" become "Auto" in `ship-loop`, `open-pr`, `build-from-plan`, `security-review` (skill and role doc), `chief-of-staff.md` and `ticket-writer.md`.
- `docs/compatibility.md`: the Usage and cost report cell, the No Hands note and G8 name Auto as `default` and drop Intelligence and Balanced.

## Leaves out

- Any model other than Auto on Cursor, and the Claude Code table.
- Pricing Auto runs (#442).
- The Cursor context reset (#343).
- The Cursor trial run (#441). This ticket lands first so #441 records the shipped routing.
- Past specs, plans and as-builts under `docs/superpowers/`.

## Acceptance

- `python3 ~/.collective-wisdom/scripts/cos_models.py cursor <role>` prints `default` with no `optimize_for` for the five thread roles, and `model: inherit` for the five subagent roles.
- No file under `agent-team/`, `AGENTS.md` or `docs/compatibility.md` names `auto-smart`, `optimize_for`, Auto Intelligence or Auto Fast as current routing.
- `python3 -I -m pytest -q agent-team/scripts` passes, and the three tests fail if a role goes back to `auto-smart` or a `.cursor` agent file pins another value.
- The documenter and both reviewers keep `readonly: true`.

## Calls I made

- The Cursor agent files use `model: inherit`, not `model: default`. Cursor's subagent doc lists only `inherit` and concrete model ids for `model:`, and does not show Auto as a frontmatter value. `inherit` is documented and, with every Cursor parent on Auto, lands the subagent on Auto too. The cost: if a user runs a Cursor thread on a non-Auto model by hand, its subagents follow it there.
- For the ten-role acceptance check, the five subagent roles print `model: inherit in .cursor/agents/<file>` rather than `default`, since the pin names what the file says. The ticket's "the `pinned` lines name the same value" read as the same value as the agent files.
- Thread routes drop the `options` key entirely instead of sending `"options": {}`. T3's model selection treats options as optional, and the printed JSON stays short.
- `test_cursor_routing.py` skips `inherit` from the agent files rather than treating it as a second unpriced exception: it names no model, and the parent's model is already collected from `cos_models.py`.
- The "Not yet observed" caveat and the strict-tolerance advice stay in `models.md`: the switch does not settle what the run store records or whether an inheriting subagent really runs on Auto.
