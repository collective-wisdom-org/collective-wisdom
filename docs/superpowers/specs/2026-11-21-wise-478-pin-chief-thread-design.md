# WISE-478: Pin the Chief of Staff thread when it starts

**Status:** Shipped
**Ticket:** [#478](https://github.com/collective-wisdom-org/collective-wisdom/issues/478)
**Shipped:** in PR #480, as specified

## Goal

In T3 Code, the Chief of Staff thread pins itself at `start the team`, take over and `resume`, so each repo's Chief of Staff thread sits at the top of the thread list.

## Today

- `agent-team/.claude/skills/chief-of-staff/startup.md` § Thread title runs at `start the team` (Setup step 4), take over and `resume` (`rotation.md` take-over step 3.1). It renames the thread with `t3_thread_update` to the line `project_config.py chief-title` prints. A failed rename adds the Cleanup line `Thread title not set: ...` and the pass carries on.
- T3 Code's `t3_thread_organize` takes `action: "pin"` and, with no `threadId`, acts on the calling thread. No Chief of Staff file calls it.
- `agent-team/docs/agents/chief-of-staff.md` says the Chief of Staff titles its own thread at those three points.

## Change

1. `startup.md` § Thread title: add a step 4 after the rename steps. Call `t3_thread_organize` with `action: "pin"` and no `threadId`. If the call fails, add the Cleanup line `Thread not pinned: <tool error>` and carry on. If the session has no `t3_thread_organize` tool, skip the step with no Cleanup line. The section's opening line also says pinning a pinned thread is a no-op, next to the rename no-op.
2. The pin runs after the rename and does not depend on it: a failed rename still pins, and a failed pin does not undo the rename.
3. `agent-team/docs/agents/chief-of-staff.md`: the line about titling the thread also says it pins the thread, and that a failed pin is one Cleanup line.

`rotation.md` step 3.1 and Setup step 4 already run § Thread title, so they need no change.

## Not changing

- Pinning ship-loop children, ticket helpers, project manager threads or any other thread.
- Unpinning on `stop everything` or when the team stops.
- Any script or test: the change is markdown only, so there is no plan; the build works from this spec.

## Acceptance

- After `start the team`, take over or `resume` in T3 Code, the Chief of Staff thread is pinned.
- Pinning an already pinned thread changes nothing and adds no Cleanup line.
- A pin failure adds one Cleanup line and never stops a pass.
- A session with no `t3_thread_organize` tool skips the step silently (a Cursor Chief of Staff in T3 Code has the tool and pins).
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Files

| File | Change |
|---|---|
| `agent-team/.claude/skills/chief-of-staff/startup.md` | § Thread title: pin step and no-op note |
| `agent-team/docs/agents/chief-of-staff.md` | Role line names the pin |

## Calls I made

- **The pin lives in § Thread title, not in a new section.** It runs at the same three points as the rename, so a step there reaches all three without touching `rotation.md` or Setup.
- **The section keeps its name, `Thread title`.** Renaming it would break the references in `startup.md` and `rotation.md` for a small gain.
- **The pin runs even when the rename fails.** The two are independent; the ticket asks for each failure to carry on.
- **An already pinned thread is treated as a no-op.** If T3 returns an error for pinning a pinned thread, that error would show as a Cleanup line; the ticket says it should not, so the build checks the tool's behaviour on a pinned thread and, if it errors, the step treats that error as success.
- **"No `t3_thread_organize`" is judged by the tool being absent from the session**, the same way other T3-only steps are skipped, with no harness check script.
- **The role doc `chief-of-staff.md` is updated** because it lists what the Chief of Staff does to its own thread.
