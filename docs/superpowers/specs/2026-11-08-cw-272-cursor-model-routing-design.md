# CW-272: Define model routing for Cursor and price the Cursor models it uses

**Status:** Draft
**Ticket:** [#272](https://github.com/collective-wisdom-org/collective-wisdom/issues/272)

## Goal

Every role and stage has a Cursor model, written next to the Claude Code table in `chief-of-staff` § Models, with the exact value a Cursor Chief of Staff passes and how each one is set. On Cursor the team runs Grok 4.7 and Composer 2.5, and no Cursor run is started on a Claude model: not a child, a project manager child, a subagent, or a fallback subagent. Every routed Cursor model has a price, so `agent_usage.py --ticket` shows a dollar cost for a Cursor run on it and No Hands doesn't stop with `cost unknown`.

## Today

Facts from `main` at `5721fa9`.

- `chief-of-staff` § Models is one table, with Claude Code values only. The model values the team passes are hard-coded to `claudeAgent` in eight places: `startup.md` step 3 (the thread's own model check), SKILL.md § Models step 2 (`t3_thread_configure` before a spec-approval relay), SKILL.md child start (`delegate_task` `target`, line 387), `continuation.md` (a continuation child starts "on the lane's model", Opus or Sonnet, line 19), `ticket-helper.md` step 1, `rotation.md` step 2 (`t3_thread_launch`), and `project-manager/reference.md` lines 8 and 64 (the Backlog ranking and hygiene children, `claude-sonnet-5-5`). A Chief of Staff on Cursor that follows the skills as written starts its children on Claude Code.
- `cos_tick.py` line 197 prints `configure <child> claude-sonnet-5-5 effort=high`, and SKILL.md line 188 tells the Chief of Staff to act on it. `test_cos_tick.py` line 110 checks that line.
- The subagent fallbacks name Claude models: when a subagent type isn't listed, `build-from-plan` (lines 27, 54) starts "a general Sonnet subagent" for the implementer and compacter, and `open-pr` starts a general Sonnet documenter (line 97) and a general Opus code reviewer (line 170). `ship-loop` § Models says "implementer `sonnet`, code review and security review `opus`". The role docs `chief-of-staff.md` line 8 and `ticket-writer.md` line 7 say Sonnet 5.5, and `security-review.md` line 3 says Opus.
- `agent-team/.cursor/agents/*.md` all set `model: inherit`. `test_agent_files.py` `test_cursor_twin_matches_the_claude_agent` requires that (`cmeta["model"] == "inherit"`). `AGENTS.md` § Agent config and `org-chart.md` line 110 say the same. With `inherit`, a reviewer started by a build child on Sonnet runs on Sonnet, not Opus.
- `security-review` SKILL.md line 25: on Cursor, start a general subagent "on the strongest model its tool offers".
- The models the Cursor provider offers in T3 Code (`orchestrator_capabilities`, today) include `grok-4.7` (options `reasoning_effort` low to xhigh, default high; `contextWindow` 256k or 500k, default 500k; `fastMode`, default on), `grok-4.6`, `composer-2.5` (option `fastMode` only, default on), `claude-opus-5-5`, `claude-sonnet-5-5`, `gemini-4-argon`, `default` (Auto) and older Claude models.
- Cursor's run store records the model id as offered: the local stores hold runs on `claude-opus-5-5`, `grok-4.7` and `default`.
- `prices.json` has the families `opus`, `sonnet`, `haiku` and `fable`. `agent_usage.family()` matches by substring, so `claude-opus-5-5` and `claude-sonnet-5-5` already price as `opus` and `sonnet`. `grok-4.7`, `composer-2.5` and `default` have no price.
- `docs/compatibility.md` G8 says "Ticket: none yet" and names `grok-4.7` as the unpriced example. The Usage and cost report row's Cursor cell says `partial: models without a price show cost unknown (G8)`.
- No Cursor run exists in `cw-cursor-trial` (no `~/.cursor/projects/*cw-cursor-trial*` store). CW-256 (#256) is open and waits on a manual Cursor run.

- Published rates, read 2026-11-08 (xAI's API page and Cursor's model docs, as cited by pricing sites): Grok 4.7 $2 input, $0.50 cached input, $6 output per million for prompts under 200K; $4, $1, $12 when a prompt is 200K or more; its Fast mode costs more. Composer 2.5 Standard $0.50 input, $0.20 cache read, $2.50 output; Fast $3, $0.50, $15. Neither lists a cache-write rate.
- `test_prices.py` checks `prices.json` against the `published` rates in `price_fixture.json`, which lists the four Claude models only. The `agent-gantt` mod reads `prices.json` and matches a family by substring too (`rows.ts` line 72).

## Design

### Routing: Grok and Composer on Cursor

The user asked for Grok and Composer on Cursor (changes on the first spec). Grok 4.7 takes the roles that ran on Opus: the spec and both reviews. Composer 2.5 takes the roles that ran on Sonnet: bookkeeping, build and merge.

| Role or stage | Cursor model | Options | How it's set on Cursor |
|---|---|---|---|
| Chief of Staff thread | `composer-2.5` | `fastMode: false` | The user picks it when starting the thread; `startup.md` step 3 checks it. The rotation successor gets it from `t3_thread_launch` |
| Ticket helper | `grok-4.7` | `reasoning_effort: high`, `fastMode: false` | `delegate_task` `target` |
| Project manager children (Backlog ranking, hygiene) | `composer-2.5` | `fastMode: false` | `delegate_task` `target` |
| Child, spec stage | `grok-4.7` | `reasoning_effort: high`, `fastMode: false` | `delegate_task` `target` |
| Child, build and merge stages | `composer-2.5` | `fastMode: false` | `t3_thread_configure` before the spec-approval relay; `delegate_task` `target` at a continuation start |
| Implementer, documenter, compacter | `composer-2.5` | none (Cursor's default) | `model:` in `.cursor/agents/<name>.md` |
| Code review, security review subagents | `grok-4.7` | none (Cursor's default) | `model:` in `.cursor/agents/<name>.md`; the security review's general subagent asks for it |

The Claude Code models stay as they are. On Cursor the Claude models, Auto, Grok 4.6 and Gemini are not used anywhere, including the subagent fallbacks below. The context window stays at Cursor's default.

### Chief of Staff skill

- § Models gets a `Cursor` subsection with the table above and the exact values: `target: {providerInstanceId: "cursor", model: ..., options: {...}}` and `modelSelection: {instanceId: "cursor", ...}`, with the option names T3 lists for each model (`reasoning_effort` and `fastMode` for Grok 4.7, `fastMode` only for Composer 2.5).
- One rule there: the Chief of Staff reads its own provider at startup (`t3_thread_configure`, no arguments, already step 3). When that's `cursor`, every model value the skill passes uses the Cursor subsection instead. The eight call sites (including the two in `project-manager/reference.md` and the continuation start) keep their Claude Code values and each gets a short "on Cursor, § Models Cursor" pointer, so no call site guesses.
- `cos_tick.py` prints `configure <child> build` in place of the Claude model id, and SKILL.md line 188 says: switch the child to the build-stage model in § Models for this thread's provider (`claude-sonnet-5-5` effort high on Claude Code, `composer-2.5` fast mode off on Cursor). `test_cos_tick.py`'s `CONFIGURE` follows.
- The `chief-of-staff.md` and `ticket-writer.md` role docs name both models, Claude Code first, then Cursor.
- `startup.md` step 3 checks for `composer-2.5` with fast mode off on Cursor.
- A note on what the CW-256 run showed. Today it says: not yet observed; the routing comes from the models Cursor offers in T3 Code. The open questions where a role may not be pinnable: whether a Cursor subagent honors a `model:` id, whether `t3_thread_configure` switches a Cursor child mid-thread, and whether the run store tells a Fast-mode run apart from a standard one.

### Cursor agent files

`agent-team/.cursor/agents/*.md` set `model:` by their Claude twin's model: `opus` becomes `grok-4.7` (code-reviewer, security-reviewer), `sonnet` becomes `composer-2.5` (implementer, documenter, compacter). `test_agent_files.py` checks that mapping in place of `inherit`. `AGENTS.md` § Agent config and `org-chart.md` line 110 say the copies pin the matching Cursor model.

### Subagent fallbacks on Cursor

- `security-review` SKILL.md line 25 asks for `grok-4.7` (`chief-of-staff` § Models). When the tool can't pick a model, the subagent runs on the child's own model (Grok or Composer), never a Claude model. "The strongest model its tool offers" goes, since on Cursor that can be Claude Opus. `security-review.md` line 3 says Grok 4.7 on Cursor.
- The "type isn't listed" fallbacks in `build-from-plan` and `open-pr` name the model by host: Sonnet or Opus on Claude Code, `composer-2.5` or `grok-4.7` on Cursor.
- `ship-loop` § Models says the subagents' Cursor models too: implementer, documenter and compacter `composer-2.5`; code review and security review `grok-4.7`.

### Prices

`prices.json` gets two families, keyed by the full model id, since `family()` and the mod match by substring and a bare `grok` would also price Grok 4.6:

- `grok-4.7`: input 2, output 6, read 0.50, write_1h 2, write_5m 2.
- `composer-2.5`: input 0.50, output 2.50, read 0.20, write_1h 0.50, write_5m 0.50.

These are the standard rates. Neither model lists a cache write, so a cache write is priced as input. `price_fixture.json` gets the two models under `published`, with their sources added to `source`, so `test_prices.py` checks them the way it checks the Claude rows.

A new test in `agent-team/scripts` collects every Cursor model the routing names, from the `model:` values in `.cursor/agents/*.md` and the backticked ids in the § Models Cursor table, and checks two things for each: `agent_usage.family(m)` is a key of `PRICES`, and the id does not contain `claude`. The same test scans the skills under `agent-team/.claude/skills/` for any `providerInstanceId: "cursor"` or `instanceId: "cursor"` value and applies the same check to its model, so a Claude model can't come back into the Cursor routing unnoticed. The routed ids also become rows in the existing `test_ticket_line_with_cursor` table, so a Cursor run on each one gives a dollar cost, not `cost unknown`. A routed model with no price then fails the tests.

### Compatibility doc

- G8: the routed Cursor models are priced (CW-272), at the standard rate. A Cursor run on a model outside the routing (Auto, Grok 4.6, Gemini) still shows `cost unknown`, and `grok-4.7` is no longer the example. The context-size half stays open with `Ticket: none yet`.
- The Usage and cost report row's Cursor cell: `partial: models outside the routing show cost unknown, and Grok long prompts and Fast mode are priced at the standard rate (G8)`. It stays partial until a Cursor run on a routed model has been priced on a real store.

## Leaves out

- Prices for Cursor models the routing doesn't use (Auto, Grok 4.6, Gemini). The Claude models on Cursor are already priced through the `opus` and `sonnet` families. Auto can't be priced anyway: the store says `default`, not the model that ran.
- Grok's long-prompt rate and both models' Fast rates.
- Routing for Codex and Antigravity.
- Changing the Claude Code models.
- Cursor context size for rotation (the other half of G8).
- The CW-256 trial run itself.

## Calls I made

- **The CW-256 evidence doesn't exist yet.** No Cursor run is in `cw-cursor-trial`. The build routes from the models Cursor offers in T3 Code and writes "not yet observed" in the note. The build files a follow-up ticket, under the same epic as CW-256, to record what the trial run shows.
- **Composer isn't an xAI model.** Cursor makes it. The user named it, so it's in the routing.
- **No Claude model on Cursor at all, including fallbacks.** The user asked for xAI models instead of Claude models on Cursor. Where the skills fall back ("a general Sonnet subagent", "the strongest model its tool offers"), the Cursor fallback is Grok, Composer or the child's own model, never Claude.
- **Grok 4.7 takes the Opus roles (spec, both reviews) and Composer 2.5 the Sonnet roles (Chief of Staff, build, merge, project manager children, implementer, documenter, compacter).** The ticket helper is the one Sonnet role that goes to Grok: a wrong **Today** section costs a spec run. Grok 4.6 isn't used: 4.7 is newer and priced.
- **`cos_tick.py` names the stage, not the model.** Its `configure` line says `build`, and the Chief of Staff looks the model up in § Models for its provider. One script then serves both hosts.
- **Fast mode off wherever the skill passes options.** Both models default to Fast on Cursor, which costs 2x (Grok) to 6x (Composer) the standard rate. The subagent files can't set it, so a subagent may run in Fast mode and its cost would be understated. The trial follow-up checks this.
- **Grok is priced at its under-200K rate.** `prices.json` holds one rate per kind. A prompt of 200K or more bills at double, so a long Grok run is understated in the report and the No Hands cap.
- **Cache writes are priced as input** for both models, since neither lists a cache-write rate.
- **The rates come from pricing sites that cite xAI's API page and Cursor's model docs**, read 2026-11-08. The build rechecks them on the official pages before writing `prices.json`.
- **The Chief of Staff picks the Cursor column from its own provider.** A Chief of Staff on Cursor then starts its children on Cursor, not Claude Code. The ticket asks only for the values and how they're set, but values that no call site reads would leave Cursor children on Claude Code.
- **Cursor subagent copies pin a model instead of `inherit`.** With `inherit`, reviewers started by a build child would run on Composer. This changes a rule `AGENTS.md` and `test_agent_files.py` state today.
- The test reads routed ids from the agent files and the § Models Cursor table, so a model added to the table without a price fails it.

## Touches

Money only as cost reporting: two new price families feed the cost report and the No Hands cost cap. No data, auth, user email or migrations. It does edit files on the approval and hands paths: the `chief-of-staff`, `project-manager`, `security-review`, `ship-loop`, `open-pr` and `build-from-plan` skills, `cos_tick.py`, `AGENTS.md`, the two reviewer agent files, and `scripts/` tests.
