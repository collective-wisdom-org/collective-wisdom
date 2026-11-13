# CW-280: Keep every Chief of Staff child on the Chief of Staff's own harness

**Status:** Shipped
**Shipped:** in PR #291, as specified
**Ticket:** [#280](https://github.com/collective-wisdom-org/collective-wisdom/issues/280)
**Related:** [#256](https://github.com/collective-wisdom-org/collective-wisdom/issues/256) (Cursor run record), [#272](https://github.com/collective-wisdom-org/collective-wisdom/issues/272) (Cursor routing), [#273](https://github.com/collective-wisdom-org/collective-wisdom/issues/273), [#275](https://github.com/collective-wisdom-org/collective-wisdom/issues/275)

## Goal

A Chief of Staff runs on one harness, and everything it starts runs on that harness too, using that harness's model routing: spec, build and merge children, the ticket helper, the project manager's ranking and hygiene children, a rotation successor, and the subagents those children start. A harness with no routing for a role blocks that role instead of borrowing another harness. A child that ends up on another harness anyway is flagged in the Chief of Staff's plan.

## Today

Facts from `main` at `34031d8`.

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Models has the Claude Code table (role, model, effort, why). § Models › Cursor (CW-272, CW-275) routes every role to `auto-smart` and applies when startup.md step 3 reads this thread's provider as `cursor`. No other harness has a table, and no sentence states the rule for every role and harness.
- The hard-coded `claudeAgent` in a template: SKILL.md § Models step 2 (`t3_thread_configure` before the spec approval relay) and § Readiness check and start step 2 (`delegate_task` `target`), `ticket-helper.md` step 1, `project-manager/reference.md` (ranking child line 8, hygiene child line 64) and `rotation.md` line 39 (`t3_thread_launch` `modelSelection`). Each says "on Cursor, § Models Cursor" after it. `continuation.md` line 19 names the Claude models in prose with the same Cursor aside.
- startup.md step 3 reads this thread's model with `t3_thread_configure` and checks it against the Claude Code row or the Cursor row. A provider that is neither has no rule.
- The review and documenter subagents come from agent files: `agent-team/.claude/agents/` (Claude Code) and `agent-team/.cursor/agents/` (Cursor). Nothing says what another harness uses.
- Every `t3_thread_read` result has `thread.providerInstanceId` and `recentRuns[].providerInstanceId` (checked on this run: the Chief of Staff thread reads `claudeAgent`). The tick's `read` and `idle-read` lines already read every active child each turn, so the provider costs no extra call.
- `cos_state.py` keeps `childThreadId` per ticket and no provider. Ticket fields are set with the `set` op and top-level keys with the `top` op (the allowed key lists are at lines 77 and 82). `cos_tick.py` prints the look plan from state alone; `cos_sweep.py` runs checks that need no thread reads. Neither checks a provider.
- `docs/compatibility.md` § Runs records the 2026-11-09 Cursor run (CW-256), where every child ran on Claude Code because the templates passed `claudeAgent`.

## Design

### 1. The rule, in SKILL.md § Models

A short paragraph at the top of § Models:

- A Chief of Staff's children (spec, build, merge, continuation), helpers (ticket helper, ranking child, hygiene child), rotation successor and the subagents those threads start all run on the Chief of Staff's own harness, with that harness's table. The harness is the provider startup.md step 3 reads.
- Every model value a template passes comes from this thread's table. No template names a provider or model itself.
- A row marked `not routed yet`, or a provider with no table, means that role does not start: the Chief of Staff starts no thread for it and reports `BLOCKED: no <role> routing for <provider>` under Needs you. It never falls back to another harness's table.

### 2. One table shape for every harness

Each harness gets a subsection `### <Harness>` with:

- A `Provider id` line: the `providerInstanceId` T3 reports for it (`claudeAgent`, `cursor`).
- A table with these rows in this order: Chief of Staff thread, Ticket helper, Project manager children, Child spec stage, Child build and merge stages, Implementer, Documenter, Compacter, Code review, Security review. Columns: Role or stage, Model, Options, Set by.
- A `Values` line with the literal `target` for each distinct row value and the `modelSelection` a switch or launch passes.

The Claude Code table moves into `### Claude Code` and takes this shape. Its values do not change: Sonnet 5.5 medium (Chief of Staff, project manager children), Sonnet 5.5 high (ticket helper, build and merge), Opus 5.5 medium (spec), the implementer pinned to Sonnet in `.claude/agents/implementer.md`, the documenter and compacter on Sonnet as their agent files pin them today, Opus for code and security review. Its `Why` notes become a short list under the table, and the Fable and Haiku "not used" rows become one sentence. The project manager children row is new in the Claude Code table; it records what `project-manager/reference.md` passes today (Sonnet 5.5 medium).

`### Cursor` already fits the shape. Its rows split "Implementer, documenter, compacter" and "Code review, security review" into one row each, with the same values. Its notes and the "Not yet observed" paragraph stay as they are.

`### Codex` and `### Antigravity` are stubs: `Provider id: not recorded yet`, and every row `not routed yet`. No model values are invented. Since startup.md step 3 can't match either provider to a recorded id, a Chief of Staff on either harness gets the "no table" path in § 1: it can report status and tickets but starts no child or helper.

The "How a child changes model" steps keep their meaning but name the table row, not a literal: step 1 starts on the spec row, step 2 switches to the build and merge row. `configure <child> build` in § Tick says "the build and merge row of this thread's table".

### 3. Templates read the table

Each hard-coded value becomes a pointer to a row of this thread's table:

| Place | Before | After |
|---|---|---|
| SKILL.md § Readiness check and start step 2 | `target: {providerInstanceId: "claudeAgent", model: "claude-opus-5-5", ...}` | `target`: the Child spec stage row of this thread's table (§ Models) |
| SKILL.md § Models step 2 | `modelSelection: {instanceId: "claudeAgent", ...}` | the Child build and merge row's `modelSelection` |
| `ticket-helper.md` step 1 | `claudeAgent`, Sonnet high | the Ticket helper row |
| `project-manager/reference.md` ranking and hygiene | `claudeAgent`, Sonnet medium | the Project manager children row |
| `rotation.md` launch | `claudeAgent`, Sonnet medium | the Chief of Staff thread row's `modelSelection` |
| `continuation.md` | Opus and Sonnet named in prose | the Child spec stage or Child build and merge row |

startup.md step 3 compares this thread's model with the Chief of Staff row of the table for its provider, and takes the "no table" path for a provider that has none.

After the change, `grep -rn claudeAgent agent-team/.claude/skills` finds `claudeAgent` only in the § Models Claude Code subsection.

### 4. Record the providers in state

- New top-level key `chiefProvider`: `{"threadId", "provider"}`, the provider of the Chief of Staff thread that recorded it. startup.md step 3 saves it with a `top` op after reading its own model; rotation.md Resume mode does the same for the successor.
- New ticket field `provider`: the child's `thread.providerInstanceId` from any `read` or `idle-read` of it. During `tick --after-reads`, a read that returns a provider different from the saved one (or none is saved) saves it with a `set` op. A failed read saves nothing.
- `cos_state.py` allows both keys. Both are plain strings that go into plan lines, so `cos_tick.py` passes them through its existing `safe()` check: an unsafe value stops the plan with exit 2, like any other unsafe state value.
- `state-keys.md` documents both.

### 5. The mismatch check, in `cos_tick.py`'s look plan

`cos_tick.py` fits better than `cos_sweep.py`: the look plan is where the child reads are printed, and it reads state alone, so the check needs no new reads. Before the other look lines, the plan adds:

- `chief-provider` when `chiefProvider` is missing or names another thread: read this thread's provider (`t3_thread_configure` with no arguments) and save it with a `top` op. No mismatch lines that turn.
- `harness-mismatch <PREFIX>-N child=<provider> chief=<provider>` for each ticket in an active or queued stage whose `provider` is set and differs from `chiefProvider.provider`.

A ticket with no `provider` gets no line (its read this turn fills it in), so a thread that can't be read never stops the pass: the plan keeps its sweep and `tick --after-reads` lines.

On a `harness-mismatch` line the Chief of Staff reports under Needs you, once per ticket while the mismatch lasts: `<PREFIX>-N runs on <child provider>, not this thread's <chief provider>. Say cancel N to stop it.` It does not stop, relay to or restart the child on its own. A new row in the § Tick plan line table says this.

Helpers are not tickets and are not in state, so they are checked where they are already read:

- ticket-helper.md § Helper test: the first read already returns `thread.providerInstanceId`. A helper on another provider still gets its report posted, with one extra line: `- Ticket helper ran on <provider>, not this thread's <provider>: [ticket helper](<link>).`
- project-manager/reference.md ranking and hygiene children: `delegate_task` returns their thread id. After the wait, one `t3_thread_read` with `limit: 1`, `maxCharsPerItem: 1` gives the provider, and a mismatch adds the same line under Cleanup.
- A rotation successor whose provider differs is caught by its own `chief-provider` line and the ticket mismatch lines that follow.

### 6. Test

One table-driven test in `agent-team/scripts/test_cos_tick.py` for the rule "a child on another provider than the Chief of Staff is flagged in the look plan, and nothing else is". Cases:

| Case | State | Expect |
|---|---|---|
| matching | chief `claudeAgent`, child `claudeAgent` | no `harness-mismatch` line |
| mismatched (the seeded case) | chief `cursor`, child `claudeAgent` | `harness-mismatch CW-5 child=claudeAgent chief=cursor` |
| missing provider | child has no `provider` | no mismatch line; plan still has `read` and `tick --after-reads` |
| unreadable thread | the child's read failed, so no `provider` was saved, alongside a mismatched child | the mismatched one is flagged, the other gets no line, the plan still ends `tick --after-reads` |
| chief unknown or stale | no `chiefProvider`, or one for another thread | `chief-provider`, no mismatch lines |

`cos_state.py` gets a case in its existing set-op table test only if the key lists need more than an entry each; a test that the keys are listed would restate the code.

### 7. Claude Code control run

The build records a control run in `docs/compatibility.md` § Runs, from the run that ships this ticket: a Claude Code Chief of Staff (`mcp:d9205ef0-…`, read as `claudeAgent`) running CW-280. The builder reads each thread this Chief of Staff started that the state file and its thread list show (children, helpers, project manager children) with a small `t3_thread_read` and records each `thread.providerInstanceId`. The entry states the count and whether any was not `claudeAgent`, next to the 2026-11-09 Cursor run. If a thread can't be read, the entry says so rather than counting it.

## Out of scope

- Changing any model, effort or option in either table (CW-272 owns the Cursor values).
- The real Cursor checks in #273 and #275.
- Choosing Codex or Antigravity models or provider ids.
- Moving a mismatched child to the right harness. The check reports; the user decides.

## Calls I made

- The check lives in `cos_tick.py`, not `cos_sweep.py`: the look plan already holds the child reads, and the sweep is for checks that read no threads.
- The provider is read from the child's thread (`thread.providerInstanceId`), not copied from the `target` the Chief of Staff passed. A recorded target would only repeat the template's mistake back to it; the thread read shows where the child actually runs, and it costs no extra call.
- A mismatch is reported and left to the user (`cancel N`). The Chief of Staff does not stop or restart the child itself, because the ticket says the check flags and does not stop a pass, and killing a child mid-build loses work.
- A harness with no table (Codex, Antigravity, anything else) starts no children or helpers at all, and the Chief of Staff still answers status and tickets. The ticket says a role with no routing blocks; with every row unrouted, that is every role.
- `chiefProvider` stores the thread id with the provider, so a rotation successor re-records its own without a separate rotation step.
- Helpers are checked where their threads are already read (helper test, after the project manager child's wait), not through state, since they have no state entry.
- The Claude Code table gains a Project manager children row (Sonnet 5.5 medium, what reference.md passes today), so both tables have the same rows. No value changes.
- The control run is this ticket's own run, recorded by the builder, rather than a separate trial.
- No release note beyond the usual PR section; nothing changes for a Claude Code or Cursor user unless a child lands on the wrong harness.
