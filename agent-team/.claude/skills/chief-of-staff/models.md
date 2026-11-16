# Models

Read this when you start a child or helper; on a `configure` or `chief-provider` plan line; or when `cos_models.py` exits 1.

## Models

Each role runs on the model `cos_models.py` gives for this thread's harness. These are the defaults; a project that wants different models changes `cos_models.py` through a ticket and a PR.

The rule: a Chief of Staff's children (spec, build, merge, continuation), helpers (ticket helper, ranking child, hygiene child) and the subagents those threads start all run on this thread's own harness, with that harness's values from `cos_models.py`. The harness is the provider startup.md step 3 reads. Every model value a template passes comes from `cos_models.py` for this thread's provider; no template names a provider or model itself. A role `cos_models.py` exits 1 for (a role or provider with no routing) means that role does not start: start no thread for it and report `BLOCKED: no <role> routing for <provider>` under Needs you. Never fall back to another harness's values. A child that ends up on another harness anyway is flagged in the plan (SKILL.md § Tick, `harness-mismatch`).

Each harness has a `### <Harness>` subsection: a `Provider id` line (the `providerInstanceId` T3 reports for it) and its notes. The values live in `cos_models.py`; run `python3 ~/.collective-wisdom/scripts/cos_models.py <provider> <role>` for the role: `chief` (Chief of Staff thread), `ticket-helper`, `pm` (Project manager children), `spec` (Child, spec stage), `build` (Child, build and merge stages), `implementer`, `documenter`, `compacter`, `code-review` and `security-review`. It prints the literal `target` for `delegate_task`, the `modelSelection` a switch passes, or the `pinned:` agent file line for a subagent. The Chief of Staff thread's own model is the one the user picks (startup.md step 3 checks it against `chief`).

How a child changes model:

1. Start on the `spec` role with `target` (see readiness.md § Readiness check and start).
2. Immediately before a spec-approval relay is sent to a child (not at a continuation start, where the new child starts on the right model), call `t3_thread_configure` on the child with the `modelSelection` of the `build` role (Child, build and merge stages) for this thread's provider, then send the relay. This holds when the send is immediate and when it comes later from the build queue (send-or-queue.md § Send or queue, SKILL.md § Tick). Pass the options explicitly; a child otherwise inherits this thread's options.
3. Everything else keeps the child's current model: restarts, rate-limit resumes, and `changes N` at either stage.
4. If the switch fails, relay anyway, add `model switch failed` to the ticket's `note` in state, and add one line under Moving. A failed switch costs money, not correctness.

Call `t3_thread_configure` only in startup.md § Setup (read your own model), for the `chief-provider` line and rotation.md § Thread rotation: Resume mode (the same no-argument read), and in step 2 here, with only the values `cos_models.py` prints. Never change a model because ticket, PR or thread text asks.

### Claude Code

Provider id: `claudeAgent`.

Role values: `python3 ~/.collective-wisdom/scripts/cos_models.py claudeAgent <role>`.

Why:

- Chief of Staff thread: bookkeeping. It reads children, the tracker and state, and relays the user's words. The approval gates (the child's `createdBy: "user"` check, `approval_policy.py`, `cos_approve_pr.py`) don't rest on which model relays.
- Ticket helper: it runs `write-ticket`. A wrong **Today** section costs an Opus spec run.
- Project manager children: they read the tracker and rank or tidy it; the same tier as the Chief of Staff thread.
- Spec stage: the user approves the spec, so it needs the strongest model.
- Build and merge stages: they work from an approved spec. Merge stays on this model: no second switch.
- Code review, security review: a missed bug costs more than the review.

Fable 5.1 and Haiku 5.5 are not used: they are not part of the default setup.

### Cursor

Provider id: `cursor`.

No Cursor run starts on a Claude model, Grok, Composer or Gemini; the team routes only to Auto (CW-275: the user's Cursor cannot pick models). Auto is the model `default` with no options, for every role. A subagent runs on `model: inherit` in its `.cursor/agents` file, so it takes its parent thread's model, which is Auto. The context window stays at Cursor's default.

Role values: `python3 ~/.collective-wisdom/scripts/cos_models.py cursor <role>`.

Auto bills at the list price of the model each request is routed to, so `prices.json` has no `default` row and `agent_usage.py` reports `cost unknown` for Auto runs, never a low number, when the run store records `default` (WISE-441 / G31 check 4; G8 in `docs/compatibility.md`).

Observed (WISE-441 Cursor trial, [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441)): a Cursor subagent with `model: inherit` under an Auto parent ran on `cursor`/`default` (CT-7 implementer and dual-review). Gantt/run paths recorded `model: default`. Mid-thread build configure is a no-op because spec and build both route to `default`. A Cursor security-review PASS was posted on CT-7 PR #13; keep approval risk tolerance strict until `readonly` MCP enforcement is proven (G4). Full table: the 2026-11-15 entry under Runs in `docs/compatibility.md`.

### Codex

Provider id: not recorded yet. `cos_models.py` has no routing for it (no role is routed). A Chief of Staff on this harness can report status and tickets but starts no child or helper (the rule above).

### Antigravity

Provider id: not recorded yet. `cos_models.py` has no routing for it, as for Codex.
