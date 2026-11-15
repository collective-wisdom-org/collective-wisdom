# CW-329: Keep the chief-of-staff rules a chief needs mid-turn inside the compaction budget

**Status:** Draft
**Ticket:** [#329](https://github.com/collective-wisdom-org/collective-wisdom/issues/329)
**Related:** [CW-315](https://github.com/collective-wisdom-org/collective-wisdom/issues/315) (the run that found it, gap G25 in `docs/compatibility.md`), [CW-316](https://github.com/collective-wisdom-org/collective-wisdom/issues/316) (reset in place)

## Goal

After a `/compact`, the part of `chief-of-staff/SKILL.md` that comes back holds every rule the chief needs to finish the turn it is in: the plan-line table, § Child path and § Guardrails. No rule is dropped; what moves stays reachable from the "When to read a reference file" table.

## Today

Facts from `main` at `da765ee`.

- `SKILL.md` is 40,540 bytes. Sections in order, with sizes: frontmatter and intro 3,946; When to read a reference file 2,632; Tools 2,657; Working set 1,641; Models 497; Lanes 1,410; State file 2,538; Tick 11,980 (its plan-line table alone 6,405); Child path 7,332; Lean turns 2,708; Guardrails 3,181.
- In the CW-315 run the compacted skill was cut at byte 20,908, mid-sentence in the plan-line table (`Cleanup line, \`Child read script u`), then `[... skill content truncated for compaction; use Read on the skill path ...]`. That fits Claude Code keeping the first 5,000 tokens or so of each skill it re-attaches after a compaction.
- The re-read line the ticket asks for is already there: line 21, added by CW-316, says to read `SKILL.md` in full (and `.agent-team/chief-notes.md`) when the text does not end with "End of chief-of-staff SKILL.md."
- `SKILL.md` § Models repeats what `models.md` § Models already says (role from `cos_models.py`, exit 1 means `BLOCKED: no <role> routing`, never fall back).
- `test_section_pointers.py` fails when a `§` pointer names a heading that is gone, so every pointer to a moved section must follow it.
- Open PRs #336 (CW-317) and #279 (CW-278) also edit `SKILL.md`. The build rebases on whatever has merged by then and measures after the rebase.

## Design

### 1. The budget

The **core** is everything from the top of `SKILL.md` to the end of § Guardrails. It must fit in **18,000 bytes**, about 86% of the 20,908 bytes that survived in the CW-315 run, leaving room for text that tokenizes worse than the sample and for later edits.

A test in `agent-team/scripts/test_agent_files.py` holds it there: in the chief-of-staff `SKILL.md`, the headings `## Tick`, `## Child path` and `## Guardrails` appear in that order, and the byte offset of the first `## ` heading after `## Guardrails` (or the end-of-file line) is at most 18,000. The failure message names the size and says to move detail into a reference file, not to raise the limit.

### 2. New order of SKILL.md

Core, in this order:

1. Frontmatter, title, the re-read line, the "You route work" paragraph and the `stop retired` / `stop paused` rules.
2. § Tick: the two calls, the exit-2 and `unsafe` rule (short form), the rerun rule, and the plan-line table.
3. § Child path: marker, pending request, stuck check, rate limit, observe.
4. § Guardrails.

After the core, still in `SKILL.md` (a full read restores them; the re-read line covers a cut):

5. § Turn start: what wakes the thread (the intro's wake list and its five bullets), the trigger table and "Not run through the tick", moved out of the intro and § Tick. They decide which tick to run, which a turn has done before it can be compacted mid-turn.
6. § When to read a reference file, with the new rows below.
7. § Lanes, § State file, § Lean turns, unchanged apart from pointers.
8. The end-of-file line.

### 3. What moves out of SKILL.md

| Text | Goes to | Read when (new or changed table row) |
|---|---|---|
| § Tools and § Working set | new `session.md`, same headings | `start the team`, `take over`, `resume`, a reset, after a compaction, or a script or tool no plan line names |
| § Models | dropped: `models.md` § Models already holds it. Pointers `SKILL.md § Models` and `chief-of-staff` § Models become `models.md § Models` | existing `models.md` row |
| The exit-2 fallbacks: the `child-read` thread-read fallback, the idle check's stdin fallback, the stuck check's wait-check fallback | new `fallbacks.md`, one section each | a `cos_child_read.py`, `cos_idle_check.py` or wait-check call exits 2 |
| **Todo start** paragraph | `readiness.md` § Todo start | existing `readiness.md` row gains "a `start-todo` plan line" |

Each moved rule keeps its wording, and the line it leaves behind in the plan-line table or § Child path is a short pointer (`Exit 2: fallbacks.md § Child read`). The compacter tightens the core's prose if the core is still over budget after the moves; it changes no rule.

### 4. Pointers

Every pointer to a moved section follows it: `SKILL.md § Tools`, `§ Working set`, `§ Models`, `§ Tick, Todo start` and `§ Tick` where it means the trigger table, across the chief-of-staff files, `project-manager`, `ship-loop` and `agent-team/docs/agents/`. `test_section_pointers.py` checks them.

### 5. Docs

`docs/compatibility.md`: G25 and check 6 of the 2026-11-14 run say the core now fits the budget the run measured, checked by the size test, and that it has not been re-run live.

## Leaves out

- Resetting the session in place (CW-316, shipped).
- A live `/compact` re-run. The PR lists it under Not proven.
- Shrinking the other skills or reference files.
- Any change to scripts, plan-line text the scripts print, gates or state.

## Calls I made

- The budget is 18,000 bytes, not tokens. Bytes need no tokenizer in CI; 18,000 is about 86% of the 20,908 bytes that survived.
- The test checks where the core ends, not the size of the whole file. The whole file stays around 35 KB; only the core has to survive a compaction.
- The trigger table, the wake list and "Not run through the tick" move below the core, into a new § Turn start in `SKILL.md`, not into a reference file. They are read on every turn, and a turn picks its trigger before it can be compacted.
- The "When to read a reference file" table moves below the core too. Plan lines and § Child path name the file they need, so a cut table costs a mid-turn chief nothing.
- § Tools and § Working set go to a new `session.md`, read at session start and after a compaction. Mid-turn the plan lines name every script.
- § Models is deleted rather than moved, since `models.md` § Models already says the same.
- The exit-2 fallbacks go to a new `fallbacks.md`. They run only when a script fails.
- **Todo start** goes to `readiness.md`, which the `start <ID>` lines already send the chief to.
- § Lanes, § State file and § Lean turns stay in `SKILL.md` below the core: they apply on every turn, and a full read brings them back.
- The ticket's "add a line near the top telling the chief to re-read SKILL.md after a compaction" is already done by CW-316 (line 21). The build keeps that line and adds nothing.
- `docs/compatibility.md` G25 is updated to say it is fixed by the size test but not re-run live.

Touches: none of these (data, money, auth, user email, migrations).
