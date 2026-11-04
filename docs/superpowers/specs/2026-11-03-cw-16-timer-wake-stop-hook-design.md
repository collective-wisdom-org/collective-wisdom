# CW-16: Decide whether the Chief of Staff needs a timer, scheduled wake or new Stop-hook check

**Ticket:** [CW-16](https://github.com/dbeallor/collective-wisdom/issues/16)
**Status:** spec, awaiting the user's answers

## Goal

CW-11 made the Chief of Staff find a lost finish notice on its next turn that makes tool calls. It added no way to make that turn happen. This ticket asks whether the wait for the next turn costs enough to need one: a timer, a scheduled wake or a new Stop-hook check. This spec gives the facts, one question per option and a recommendation with its reason. It decides nothing itself: every answer is the user's (see § Open questions).

## Non-goals

- Changing T3's notice rule.
- The sweep, the handoff block and the ready check from CW-11.
- The idle check, chain walk, gates, lane limits and models (CW-15 asks about those).
- Continuation children for restarts, answers and resumes (CW-14).
- Acting on an answer early through state, memory, a scheduled task or a child's task text. A picked change ships in this PR, and the current skill stays in force until it merges.

## Today

Facts from `main` at `388dab1` (CW-11 merged as #22 at 2026-11-04 01:34 UTC).

| Part | Where it lives | What it does today |
|---|---|---|
| What wakes the Chief of Staff | `chief-of-staff` intro, frontmatter | Start-up (`start the team`, `take over`, `resume`), a message from the user, a child's run finishing, and the rate-limit wake. "There is no timer." |
| Schedules | `chief-of-staff` § Guardrails, § Tools, § Full pass step 4 | "The Chief of Staff schedules nothing except the rate-limit wake." `schedule_task` is allowed only for that wake and the start-up clean-up. |
| Old heartbeat | `chief-of-staff` § Start-up clean-up, § Commands | An older design ran `run /chief-of-staff heartbeat` every 30 minutes. It was removed in the fathom team before this repo existed; start-up clean-up still deletes any leftover task. Its removal reason is not recorded in this repo. |
| Stop hook | `agent-team/.claude/settings.json`, § Thread rotation | One hook: `cos_rotation_check.py --hook`. It sends the turn back when the check prints `rotate:`, so a skipped rotation check still runs. |
| Lost-notice finders | § Sweep, § Lean turns idle check | The sweep (merged, ready and parent checks, no thread reads) and the idle check (one tiny read per active child). Both run only on turns that already happen. |
| Why notices get lost | § Send or queue | T3 sends a finish notice only to the run's parent, and only when that parent started the run or it ended on a background-command wake. A relay sent by `t3_thread_send` to a child whose parent isn't this thread reports to nobody. |

### When the wait happens

A lost finish waits only when no other wake comes. Any finish notice from any other active child, and any message from the user, starts a turn that runs the sweep. So the wait is long only when:

1. a relay went to a child whose parent isn't this thread (a child from a retired Chief of Staff, or one with its own parent, like PR #18's), **and**
2. that child was the last one running, or every other active child is also quiet, **and**
3. the user doesn't write.

Then the result (`SPEC READY`, `MERGE READY`, `BLOCKED:`) sits unreported, and a slot it frees stays empty, until the user writes. Overnight that can be hours.

### Evidence looked for

- **Lost notices since CW-11.** CW-11 merged about 15 minutes before this spec. The current Chief of Staff thread starts at 01:36 UTC. In it, one relay matched case 1 above: the merge approval for PR #18, whose child had its own parent. The Chief of Staff said "T3 may not send me a finish notice". The merge was reported on the next turn, under a minute later, because other children were active. No lost notice waited for a wake.
- **Before CW-11.** CW-11's trace from fathom (GUY-327) shows lost notices that the existing checks missed because the thread skipped them, not because no turn came. That is the cause CW-11 fixed.
- **No history to measure.** `.agent-team/state.json` keeps current state only, so there is no record of how long a ticket sat before a sweep found it.

So the cost is real in principle (cases 1 to 3 above) and unmeasured in practice.

## The three options

**Timer.** A Chief of Staff turn that keeps itself running (a `sleep` loop, `ScheduleWakeup`, `Monitor`) and re-checks on a beat. The thread stays Working the whole time, each tick adds to a thread that every turn re-reads (§ Lean turns), and T3's own rules for this harness forbid waiting with sleep loops or wakeups. It also finds nothing a scheduled wake wouldn't.

**Scheduled wake.** A `schedule_task` bound to this thread, like the rate-limit wake, whose prompt runs the sweep and the idle check. This is the only option that can start a turn when nothing else does. Its cost is one Chief of Staff turn per fire, and each turn re-reads the whole thread. The old 30-minute heartbeat was this, always on. A narrower form is possible: arm it only while an active ticket's child has a parent other than this thread (case 1, the only known way a notice is lost), and delete it when none is left.

**New Stop-hook check.** A Stop hook runs when a Chief of Staff turn ends. It can't start a turn in an idle thread, so it can't shorten the wait this ticket is about. What it could do is check that the turn ran the sweep, the way the rotation hook checks rotation. That targets CW-11's cause 2 (skipped checks), which CW-11 already cut to one command.

## Open questions

Each question is the user's call. My recommendation and the reason follow each one.

1. **Is the wait for the next wake a real cost today?**
   **Recommend: not yet, so record "no" and revisit on evidence.** The window since CW-11 is minutes long and holds one case-1 relay, found within a minute. The long wait needs all three conditions at once, and CW-14 (continuation children for restarts, answers and resumes) will make case 1 rarer still. Revisit if a report shows `found by the sweep` or `found by the idle check` for a ticket that sat an hour or more, or the user finds a finished child the team never reported.

2. **Timer: build it?**
   **Recommend no.** It is the scheduled wake with worse costs: the thread never rests, every tick grows the context every turn re-reads, and this harness forbids the waiting tools it needs.

3. **Scheduled wake: build it?**
   Options: (a) no; (b) the narrow wake: armed only while an active ticket's child has a parent other than this thread, every 30 minutes, prompt `run /chief-of-staff sweep`, deleted when no such ticket is left, by `stop everything` and by take over; (c) an always-on heartbeat.
   **Recommend (a) now, with (b) as the design to build if question 1's evidence shows up.** (b) is the only option that fixes the wait, but it costs a full-thread turn per fire, adds a second scheduled task with its own state keys, clean-up and rotation steps, and today there is no lost notice for it to find. (c) is the heartbeat the older design dropped, and it fires even when no notice can be lost.

4. **New Stop-hook check: build it?**
   **Recommend no.** A Stop hook can't wake an idle thread, so it doesn't address this ticket's wait. As a "did you run the sweep" check it would need the sweep to leave a trace (a new state key or file), and nothing shows the sweep being skipped since CW-11 made it one command.

5. **Cheaper interim step: tell the user when a relay may finish unannounced?**
   Not one of the three options; it adds no schedule. When § Send or queue sends a relay to a child whose parent isn't this thread, the report gets one Moving line: `<PREFIX>-N: I may not hear when this run ends; say status to check.` The Chief of Staff already wrote this by hand for PR #18.
   **Recommend yes.** It costs one line, it tells the user the only thing that ends the wait today is their message, and it touches no schedule or hook. It does overlap CW-12, which rewrites the report layout; if CW-12 merges first, the line goes in CW-12's Moving group.

## Design

What the build stage does depends on the answers.

- **Every option "no" (questions 2 to 4), with or without question 5.** Post one comment on #16 with each question, its answer and its reason (the acceptance criterion). The PR carries this spec, its as-built, index entry and release note. Question 5 "yes" adds its one line to the skill; otherwise no skill or script change.
- **Question 3 (b) "yes".** Built in this PR, under `agent-team/`, and the skill names the schedule (the ticket's rule that a schedule, if added, is written down in the skill):
  - `cos_state.py`: two new top-level keys, `sweepWakeTaskId` and `sweepWakeEvery` (minutes), accepted by `apply` and shown by `show`. One table-driven test for the new keys.
  - `chief-of-staff` SKILL.md: arm the wake in § Send or queue when it sends to such a child; delete it in the sweep's turn when no such child is left; handle it in § Start-up clean-up, § Deleting the wake, § Commands (new `run /chief-of-staff sweep` row: idle check and sweep, then § Slot fill, no full pass), § Thread rotation take over, § State file, § Guardrails and the intro and frontmatter ("no schedule" and "schedules nothing except").
  - `chief-of-staff` reference.md § Thread rotation "Retired thread": its sweep wake firing gets only the `Moved to` reply, like the rate-limit wake.
- **Question 4 "yes".** A larger change: the record asks the Chief of Staff for its own ticket, since the hook needs a sweep trace this ticket doesn't define.
- **Question 3 (c) "yes".** Against my recommendation; the build follows the same sections as (b), without the arming condition.
- **Question 2 "yes".** Against my recommendation; the record asks the Chief of Staff for its own ticket, since the T3 rule against waiting loops would have to change first.

### Sections a change would touch

Other open work edits `agent-team/.claude/skills/chief-of-staff/SKILL.md`: PR #26 (CW-17), the CW-12 build and the CW-14 and CW-15 specs. If every answer is "no", this ticket edits no skill file. Otherwise, by question:

| Question | Sections a change would edit |
|---|---|
| 3 (b) or (c), scheduled wake | `chief-of-staff` frontmatter `description`, intro paragraph, § Tools (`schedule_task` line), § Start-up clean-up, § Deleting the wake, § State file, § Send or queue, § Sweep, § Thread rotation "Take over" step 2, § Commands (new row, `stop everything` row), § Guardrails; `chief-of-staff/reference.md` § Thread rotation "Retired thread"; `scripts/cos_state.py` |
| 4, Stop hook | `agent-team/.claude/settings.json`, § Thread rotation (hook sentence), § Sweep, a new or changed script |
| 5, report line | § Send or queue (cause paragraph), § Report format (Moving line) |

## Testing

All "no": nothing to test beyond the existing suite (`python3 -I -m pytest -q agent-team/scripts`). Question 3 (b) gets one table-driven test in `test_cos.py` for the new state keys (accepted, typed, cleared together). Question 5 is prose and gets no test, per `AGENTS.md` § Testing.

## Calls I made (surprising first)

- ⚠ I added question 5, which the ticket doesn't ask. It is the cheapest way to shorten the wait (the user knows to ask) and needs no schedule or hook.
- ⚠ I counted the ticket's "use any lost notice seen after CW-11 as evidence" as satisfied by a 15-minute window with one case and no wait. There is no more evidence to have yet. Waiting longer would mean holding a spec slot with no work.
- For the narrow wake I picked 30 minutes (the old heartbeat's interval) and the prompt `run /chief-of-staff sweep`. Both are only design notes until question 3 gets a "yes".
- I treated "timer" as a turn that keeps itself running, and "scheduled wake" as a `schedule_task`, since those are the two ways a T3 thread can act on its own clock.
- A "yes" to question 4 becomes a new ticket rather than a build here: it needs a design for the sweep trace that this spec would be guessing at.
