# CW-16: Decide whether the Chief of Staff needs a timer, scheduled wake or new Stop-hook check

**Ticket:** [CW-16](https://github.com/dbeallor/collective-wisdom/issues/16)
**Status:** Shipped

## Goal

CW-11 made the Chief of Staff find a lost finish notice on its next turn that makes tool calls. It added no way to make that turn happen. This ticket asks whether the wait for the next turn costs enough to need one: a timer, a scheduled wake or a new Stop-hook check. This spec gives the facts, one question per option and a recommendation with its reason. The user has answered each one (see § Decisions): no timer, no scheduled wake, no new Stop-hook check, and one new report line.

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

## Decisions

The user answered through the Chief of Staff: "Add one report line when a relay may finish unannounced ("I may not hear when this run ends; say status to check")? Recommend yes. It's cheap and needs no schedule or hook, but it overlaps CW-12's report layout. This question wasn't in the ticket; the child added it. do only this". The Chief of Staff read that as yes to question 5 and no to questions 1 to 4, as recommended.

| # | Question | Answer | Reason |
|---|---|---|---|
| 1 | Is the wait for the next wake a real cost today? | No, not yet | The window since CW-11 holds one case-1 relay, found within a minute. The long wait needs cases 1 to 3 at once, and CW-14 makes case 1 rarer. Revisit if a report shows `found by the sweep` or `found by the idle check` for a ticket that sat an hour or more, or the user finds a finished child the team never reported. |
| 2 | Timer | No | It is the scheduled wake with worse costs: the thread never rests, every tick grows the context every turn re-reads, and this harness forbids the waiting tools it needs. |
| 3 | Scheduled wake | No | It is the only option that ends the wait, but it costs a full-thread turn per fire and adds a second scheduled task with its own state, clean-up and rotation steps, with no lost notice yet for it to find. If question 1's evidence shows up, the narrow form (armed only while an active ticket's child has a parent other than this thread, deleted when none is left) is the one to file. An always-on heartbeat is what the older design dropped. |
| 4 | New Stop-hook check | No | A Stop hook can't wake an idle thread, so it doesn't touch this wait. As a "did you run the sweep" check it would need a sweep trace, and nothing shows the sweep being skipped since CW-11 made it one command. |
| 5 | One report line when a relay may finish unannounced | Yes | One line tells the user that their message is the only thing that ends the wait today. It adds no schedule, hook or script. |

The Chief of Staff's rule "schedules nothing except the rate-limit wake" and the intro's "There is no timer" stay as they are.

## Design

Two things ship in this PR.

### 1. The report line

One short paragraph in `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Send or queue, after the two bullets and "A queued relay stores the relay text only". It is its own paragraph, not part of the first bullet, because that bullet applies only to a send at once and a queued relay is sent later by § Slot fill step 3:

> Whenever a relay is sent with `t3_thread_send`, at once or later from the queue (§ Slot fill), and the ticket's `parentThreadId` isn't this thread's ID, T3 won't send this thread a finish notice for the run (see below). Report it under Moving: `<PREFIX>-N: I may not hear when this run ends; say status to check.` A continuation child (below) starts under this thread instead of being sent to, so it gets no such line.

- It fires on every send that goes through § Send or queue, at once or from the queue, so a queued relay sent later by § Slot fill gets the line in that turn's report. That includes a queued approval written in an older thread, which always goes to the old child.
- It does not fire for a continuation child: that path starts a new child with `delegate_task` under this thread instead of sending, so its notices arrive.
- The line goes under Moving like the other one-off lines in this section (`moved to a new child`, `model switch failed`). § Report format is not edited.

### 2. The record

One comment on #16 with each question, its answer and its reason (the table above), which is the ticket's acceptance criterion. The PR carries this spec, the plan, the as-built, the index entry and the release note.

### Sections touched, and overlap with other open work

Only `chief-of-staff` SKILL.md § Send or queue, one new paragraph after the bullets. Nothing else in the skill, no script, no hook, no `settings.json`.

- **CW-12** (building) edits § Commands `status` row, § Approval requests and § Report format (the `Needs you` example and a new `### Status layout`). It does not touch § Send or queue or the Moving group. Under CW-12 a `status` answer has no Moving section, so this line shows in the report of the turn that sent the relay, not in a later `status`. That is where it is useful: it tells the user to ask for `status`.
- **CW-14** (spec) rewrites two later paragraphs of § Send or queue (the "keeps its child" paragraph and the T3 notice-rule paragraph) and the "Continuation child" subsection. It doesn't touch the first bullet or the paragraph this PR adds. Once CW-14 ships, fewer relays go to old children, so the line shows less often.
- **CW-17** (PR #26) adds § Commands rows and a § Guardrails line. No overlap.
- **CW-15** (spec) changes no § Send or queue text.

## Testing

Prose only, so no new test, per `AGENTS.md` § Testing. The existing suite (`python3 -I -m pytest -q agent-team/scripts`) and `shellcheck install.sh agent-team/scripts/*.sh` must still pass. Manual check: `git diff main` touches only that new paragraph in the skill, plus closeout docs.

## Calls I made (surprising first)

- ⚠ The line covers only relays sent through § Send or queue. The stuck-check restart in § Full pass step 3 and the send-backs in § Approval requests (`spec not found`, the `MERGE READY` mismatch) also use `t3_thread_send` and can finish unannounced, but they don't go through § Send or queue, and CW-14 is rewriting that path into continuation children. Adding it here would mean editing a section CW-14 changes and going past "do only this".
- ⚠ The rule sits in § Send or queue, not § Report format, so this PR stays out of CW-12's sections. That matches how the section already reports `moved to a new child`.
- A merge relay for a PR with no ticket in state (PR #18's case) doesn't go through § Send or queue, so it gets no line. The Chief of Staff wrote the warning by hand there; this ticket doesn't make that automatic.
- I counted the 15 minutes since CW-11 merged as the evidence the ticket asks for, rather than holding a spec slot to collect more.
- "Timer" means a turn that keeps itself running; "scheduled wake" means a `schedule_task`.
