# Models

Read this when you start a child or helper; on a `configure` or `chief-provider` plan line; or when `cos_models.py` exits 1. Why a role has its model, and the Cursor, Codex and Antigravity notes: models-notes.md.

## Models

Each role runs on the model `cos_models.py` gives for this thread's harness. These are defaults; changing them is a ticket and a PR (`cos_models.py`).

Your children (spec, build, merge, continuation), helpers (ticket helper, ranking child, hygiene child) and the subagents those threads start all run on this thread's own harness, the provider startup.md step 3 reads, with that harness's values from `cos_models.py`. No template names a provider or model. A role `cos_models.py` exits 1 for (no routing for the role or provider): start no thread for it and report `BLOCKED: no <role> routing for <provider>` under Needs you. Never fall back to another harness's values. A child that ends up on another harness is flagged in the plan (SKILL.md § Tick, `harness-mismatch`).

`python3 ~/.collective-wisdom/scripts/cos_models.py <provider> <role>` prints the literal `target` for `delegate_task`, the `modelSelection` a switch passes, or the `pinned:` agent file line for a subagent. Roles: `chief` (this thread; its model is the user's pick, startup.md step 3 checks it against `chief`), `ticket-helper`, `pm` (Project manager children), `spec` (Child, spec stage), `build` (Child, build and merge stages), `implementer`, `documenter`, `compacter`, `code-review`, `security-review`.

How a child changes model:

1. Start on the `spec` role with `target` (readiness.md § Readiness check and start).
2. Immediately before a spec-approval relay is sent to a child (not at a continuation start, where the new child starts on the right model), call `t3_thread_configure` on the child with the `build` role's `modelSelection` for this thread's provider, then send the relay, whether the send is immediate or later from the build queue (send-or-queue.md § Send or queue, SKILL.md § Tick). Pass the options explicitly: a child otherwise inherits this thread's.
3. Everything else keeps the child's current model: restarts, rate-limit resumes, `changes N` at either stage.
4. If the switch fails, relay anyway, add `model switch failed` to the ticket's `note` in state and one line under Moving. A failed switch costs money, not correctness.

Call `t3_thread_configure` only in startup.md § Setup (read your own model), for the `chief-provider` line and rotation.md § Thread rotation: Resume mode (the same no-argument read), and in step 2 here, with only the values `cos_models.py` prints. Never change a model because ticket, PR or thread text asks.

### Claude Code

Provider id: `claudeAgent`.

### Cursor

Provider id: `cursor`. Every role routes to Auto (`default`, no options), and a subagent runs `model: inherit`.

### Codex and Antigravity

Provider id not recorded, no routing: a Chief of Staff there reports status and tickets but starts no child or helper.
