# CW-177: Rename the awaiting-spec stage to awaiting-build, and SPEC READY to BUILD READY

**Status:** Draft
**Ticket:** [#177](https://github.com/collective-wisdom-org/collective-wisdom/issues/177)

## Goal

The `awaiting-spec` stage is the wait for the user to approve the build: the spec is already written. Rename it `awaiting-build`, so it reads like `awaiting-merge` and `awaiting-review`, which name what they wait for.

Scope change from the user (ticket comment on #177): "specify that spec ready should also be renamed to build ready". The ticket body said to keep the `SPEC READY` signal. The newer instruction wins, so the child's `SPEC READY` marker becomes `BUILD READY` too, matching `MERGE READY`: both name the approval being asked for.

## Today

Facts from `main` at `84987a1`.

**The stage.**

- `agent-team/scripts/cos_state.py`: `STAGES` and `STAMPED` list `awaiting-spec`, the docstring names it, and `show`'s summary prints `awaiting-spec=<n>`. `load()` reads the state file and returns it as is; any `apply` saves it.
- `agent-team/scripts/approval_policy.py`: `auto <PREFIX>-N spec` requires the stage `awaiting-spec` (or a queued spec relay) and prints `not in awaiting-spec` otherwise. It reads state through `cos_state.load`.
- `agent-team/.claude/mods/status-pane/hooks/groups.ts`: the group "Awaiting build approval" matches the stage `awaiting-spec`. It reads `state.json` itself, and a ticket whose stage matches no group is not shown.
- Docs that name the stage: `chief-of-staff/SKILL.md`, `approvals.md`, `status.md`, `state-keys.md`, `startup.md`, `continuation.md`, `project-manager/SKILL.md`, and `agent-team/docs/agents/org-chart.md` (the stage diagram).
- Tests: `test_cos.py`, `test_approval_policy.py`, `test_cos_handoff.py`.
- No other script compares stage names to `awaiting-spec`. `cos_handoff.py` only prints the stage.

**The marker.** No script parses `SPEC READY`; the Chief of Staff reads it from the child's last message by following its skill.

- `ship-loop/SKILL.md`: the phase 1 end block, the run endings list, and § Approvals ("after your latest `SPEC READY`").
- `kickoff-feature/SKILL.md` step 5.
- `chief-of-staff/SKILL.md`: the file table, the full read (step 2), the child task template ("Stop at SPEC READY"), the stuck-child text, the adopt rule, the report lines and the slot reasons `(spec ready)` and `spec ready, found by the sweep`.
- `chief-of-staff/approvals.md` (when to read it, the "push it and report SPEC READY again" send-back, the request line `<PREFIX>-210 spec ready: …`), `startup.md` (state rebuild), `status.md` (an example row).
- `agent-team/docs/agents/org-chart.md`: both diagrams.
- `agent-team/scripts/cos_ready_check.py`: the docstring and `--help` description only.
- `test_approval_policy.py` uses `Spec ready.` as sample status text.

## Builds

1. **Stage rename.** `awaiting-spec` becomes `awaiting-build` in `cos_state.py` (`STAGES`, `STAMPED`, docstring, `show` summary `awaiting-build=<n>`), `approval_policy.py` (check, message `not in awaiting-build`, docstring), `groups.ts`, and every doc listed under Today.
2. **Old state still loads.** `cos_state.load()` rewrites a ticket whose `stage` is `awaiting-spec` to `awaiting-build` in the returned state, so `show`, `apply` and `approval_policy.py` all see the new name and the next `apply` saves it. Nothing else about the ticket changes (`lastSeenAt` keeps its value, so a pending `approve N` still counts). This is the one place `awaiting-spec` stays in `agent-team/`.
3. **Marker rename.** `SPEC READY` becomes `BUILD READY` in every file listed under Today, the child task template included. The lower-case report wording follows: the approval request line reads `<PREFIX>-N build ready: <title>. Risk: …`, and the slot reasons read `(build ready)` and `build ready, found by the sweep`.
4. **Old marker still counts.** A child started before the merge was told to stop at `SPEC READY`. The Chief of Staff's full read (`chief-of-staff/SKILL.md` § Full pass step 2) and state rebuild (`startup.md`) treat a last message ending in `SPEC READY` as `BUILD READY`. One short sentence in each place; these two, plus ship-loop § Approvals (a continuation child's "after your latest `BUILD READY`", which also accepts an older `SPEC READY`), are the only places `SPEC READY` stays in `agent-team/`.
5. **Tests.**
   - `test_cos.py`: one table-driven test: a state file with tickets in `awaiting-spec` and `awaiting-build` loads (through `show` and through an `apply`) with both in `awaiting-build`, `lastSeenAt` unchanged, and the saved file holds `awaiting-build`.
   - Existing tests switch their fixtures to `awaiting-build` and `Build ready.` with no new cases.

## Leaves out

- Old specs, plans, as-built files and release notes under `docs/superpowers/` that say `awaiting-spec` or `SPEC READY`. They record what was true then.
- The `spec` and `spec-queued` stages, the Spec lane and the "Awaiting build approval" label. Only the waiting stage and the marker change.
- The `Risk:` status-line rule.
- Old `status` text in state such as `awaiting-spec since 14:40: …`. It is prose, and the next stage op replaces it.
- A conversion in the status pane. It reads `state.json` itself, so a ticket still saved as `awaiting-spec` is missing from the pane until the Chief of Staff's next `apply`, which any state change makes.

## Calls I made (surprising first)

- **The lower-case wording moves too.** The user named the signal, but the approval request line `CW-210 spec ready: …` and the slot reasons `(spec ready)` are the same signal said to the user, so they become `build ready`. Leaving them would show "spec ready" in reports next to a `BUILD READY` marker.
- **The Chief of Staff accepts the old `SPEC READY` for in-flight children,** with no end date. Children already running hold a task that says "Stop at SPEC READY"; without this the Chief of Staff would miss their report. It costs one sentence in two places.
- **The status pane does not convert `awaiting-spec`.** The ticket's acceptance wants `awaiting-spec` only in the load-time conversion. The gap lasts until the Chief of Staff's next state write.
- **`load()` converts but does not save.** `approval_policy.py` and `show` load state read only; writing from them would be a new side effect. The next `apply` saves.
- **This edits `approval_policy.py`, which is on the approval path.** Only the stage name in its check changes, but the spec cannot be auto-approved (`ship-loop` § Approvals), and the tolerance is `strict` anyway.

## Acceptance

- `grep -r awaiting-spec agent-team` finds only the conversion in `cos_state.py` and its test.
- `grep -r "SPEC READY" agent-team` finds only the old-marker sentences in `chief-of-staff/SKILL.md` § Full pass, `startup.md` and `ship-loop` § Approvals.
- A test loads a state file with a ticket in `awaiting-spec` and gets `awaiting-build`.
- The suite from `docs/agents/project.md` § Commands passes, and the status-pane tests (`node --test`) pass.

## Touches

None of these: data, money, auth, user email, migrations. It does change a stage name in the Chief of Staff's state file, with a load-time conversion for old files.
