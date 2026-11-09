# CW-272: Define model routing for Cursor and price the Cursor models it uses

**Status:** Draft
**Ticket:** [#272](https://github.com/collective-wisdom-org/collective-wisdom/issues/272)

## Goal

Every role and stage has a Cursor model, written next to the Claude Code table in `chief-of-staff` § Models, with the exact value a Cursor Chief of Staff passes and how each one is set. Every routed Cursor model has a price, so `agent_usage.py --ticket` shows a dollar cost for a Cursor run on it and No Hands doesn't stop with `cost unknown`.

## Today

Facts from `main` at `5721fa9`.

- `chief-of-staff` § Models is one table, with Claude Code values only. The model values it passes are hard-coded to `claudeAgent` in five places: `startup.md` step 3 (the thread's own model check), SKILL.md § Models step 2 (`t3_thread_configure` before a spec-approval relay), SKILL.md child start (`delegate_task` `target`, line 387), `ticket-helper.md` step 1, and `rotation.md` step 2 (`t3_thread_launch`). A Chief of Staff on Cursor that follows the skill as written starts its children on Claude Code.
- `agent-team/.cursor/agents/*.md` all set `model: inherit`. `test_agent_files.py` `test_cursor_twin_matches_the_claude_agent` requires that (`cmeta["model"] == "inherit"`). `AGENTS.md` § Agent config and `org-chart.md` line 110 say the same. With `inherit`, a reviewer started by a build child on Sonnet runs on Sonnet, not Opus.
- `security-review` SKILL.md line 25: on Cursor, start a general subagent "on the strongest model its tool offers".
- The models the Cursor provider offers in T3 Code (`orchestrator_capabilities`, today) include `claude-opus-5-5` (options `effort`, `contextWindow` 300k or 1m, default 1m, `fastMode`) and `claude-sonnet-5-5` (options `reasoning_effort`, `contextWindow`). Sonnet's effort option on Cursor is named `reasoning_effort`, not `effort`. Also offered: `default` (Auto), `grok-4.7`, `grok-4.6`, `composer-2.5`, `gemini-4-argon` and older Claude models.
- Cursor's run store records the model id as offered: the local stores hold runs on `claude-opus-5-5`, `grok-4.7` and `default`.
- `prices.json` has the families `opus`, `sonnet`, `haiku` and `fable`. `agent_usage.family()` matches by substring, so `claude-opus-5-5` and `claude-sonnet-5-5` already price as `opus` and `sonnet`. `grok-4.7`, `composer-2.5` and `default` have no price.
- `docs/compatibility.md` G8 says "Ticket: none yet" and names `grok-4.7` as the unpriced example. The Usage and cost report row's Cursor cell says `partial: models without a price show cost unknown (G8)`.
- No Cursor run exists in `cw-cursor-trial` (no `~/.cursor/projects/*cw-cursor-trial*` store). CW-256 (#256) is open and waits on a manual Cursor run.

## Design

### Routing: Cursor runs the same Claude models

| Role or stage | Cursor model | Effort | How it's set on Cursor |
|---|---|---|---|
| Chief of Staff thread | `claude-sonnet-5-5` | `reasoning_effort: medium` | The user picks it when starting the thread; `startup.md` step 3 checks it. The rotation successor gets it from `t3_thread_launch` |
| Ticket helper | `claude-sonnet-5-5` | `reasoning_effort: high` | `delegate_task` `target` |
| Child, spec stage | `claude-opus-5-5` | `effort: medium` | `delegate_task` `target` |
| Child, build and merge stages | `claude-sonnet-5-5` | `reasoning_effort: high` | `t3_thread_configure` before the spec-approval relay |
| Implementer, documenter, compacter | `claude-sonnet-5-5` | inherited | `model:` in `.cursor/agents/<name>.md` |
| Code review, security review subagents | `claude-opus-5-5` | inherited | `model:` in `.cursor/agents/<name>.md`; the security review's general subagent asks for it |

The Claude Code models stay as they are. Fable, Haiku, Auto, Grok, Composer and Gemini are not used.

### Chief of Staff skill

- § Models gets a `Cursor` subsection with the table above and the exact values: `target: {providerInstanceId: "cursor", model: ..., options: {...}}` and `modelSelection: {instanceId: "cursor", ...}`, with the option names Cursor uses (`effort` for Opus, `reasoning_effort` for Sonnet). Context window and fast mode are left at Cursor's defaults.
- One rule there: the Chief of Staff reads its own provider at startup (`t3_thread_configure`, no arguments, already step 3). When that's `cursor`, every model value the skill passes uses the Cursor subsection instead. The five call sites keep their Claude Code values and each gets a short "on Cursor, § Models Cursor" pointer, so no call site guesses.
- `startup.md` step 3 checks for `claude-sonnet-5-5` at `reasoning_effort` `medium` on Cursor.
- A note on what the CW-256 run showed. Today it says: not yet observed; the routing comes from the models Cursor offers in T3 Code. The cases where a role can't be pinned are the open questions: whether a Cursor subagent honors a `model:` id, and whether `t3_thread_configure` switches a Cursor child mid-thread.

### Cursor agent files

`agent-team/.cursor/agents/*.md` set `model:` to the Cursor id that matches the Claude twin: `opus` becomes `claude-opus-5-5`, `sonnet` becomes `claude-sonnet-5-5`. `test_agent_files.py` checks that mapping in place of `inherit`. `AGENTS.md` § Agent config and `org-chart.md` line 110 say the copies pin the matching Cursor model.

### Security review on Cursor

`security-review` SKILL.md line 25 asks for `claude-opus-5-5` (`chief-of-staff` § Models), or the strongest model the tool offers when it can't pick one.

### Prices

No new `prices.json` entry: both routed models already match a family. A test in `agent-team/scripts` collects every Cursor model the routing names, from the `model:` values in `.cursor/agents/*.md` and the backticked ids in the § Models Cursor table, and checks each one:

- `agent_usage.family(m)` is a key of `PRICES`, and
- a Cursor run on it gives `ticket_line` a dollar cost, not `cost unknown`, by adding the routed ids as rows to the existing `test_ticket_line_with_cursor` table.

A routed model with no price then fails the test.

### Compatibility doc

- G8: the routed Cursor models are priced (CW-272). A Cursor run on a model outside the routing (Auto, Grok, Composer) still shows `cost unknown`. The context-size half stays open with `Ticket: none yet`.
- The Usage and cost report row's Cursor cell: `partial: models outside the routing show cost unknown (G8)`. It stays partial until a Cursor run on a routed model has been priced on a real store.

## Leaves out

- Prices for Cursor models the routing doesn't use (Auto, Grok, Composer, Gemini). Auto can't be priced anyway: the store says `default`, not the model that ran.
- Routing for Codex and Antigravity.
- Changing the Claude Code models.
- Cursor context size for rotation (the other half of G8).
- The CW-256 trial run itself.

## Calls I made

- **The CW-256 evidence doesn't exist yet.** No Cursor run is in `cw-cursor-trial`. The build routes from the models Cursor offers in T3 Code and writes "not yet observed" in the note. A follow-up ticket records what the trial run shows, filed by the build under the same epic as CW-256.
- **Cursor runs the same Claude models as Claude Code**, not a cheaper Cursor model such as Composer or Grok. Same quality bar at each gate, and both are already priced, so `prices.json` gets no new entry. The ticket expected new price entries; the new test still covers every routed model.
- **The Chief of Staff picks the Cursor column from its own provider.** This changes how a Chief of Staff on Cursor starts its children: on Cursor, not Claude Code. The ticket asks only for the values and how they're set, but values that no call site reads would leave Cursor children on Claude Code.
- **Cursor subagent copies pin a model instead of `inherit`.** With `inherit`, reviewers started by a build child run on Sonnet. This changes a rule `AGENTS.md` and `test_agent_files.py` state today. If Cursor turns out not to honor a `model:` id, the trial follow-up says so.
- Sonnet's effort is passed as `reasoning_effort` on Cursor, since that's the option name T3 lists for it there.
- Context window (1m by default) and fast mode stay at Cursor's defaults.
- The test reads routed ids from the agent files and the § Models Cursor table, so a model added to the table without a price fails it.

## Touches

None of these (data, money, auth, user email, migrations). It does edit files on the approval and hands paths: the `chief-of-staff` and `security-review` skills, `AGENTS.md`, the two reviewer agent files, and `scripts/` tests.
