# CW-15: Decide whether to change the idle check, chain walk, approval gates, lane limits or models

**Ticket:** [CW-15](https://github.com/dbeallor/collective-wisdom/issues/15)
**Status:** Shipped

## Goal

CW-11 fenced off five Chief of Staff parts on purpose. This ticket asks one question about each. The user answers each one with "change it" or "leave it". This spec gives the facts behind each question and a recommendation with its reason. It decides nothing itself: every answer is the user's (see § Open questions).

## Non-goals

- The lost-notice and handoff work from CW-11.
- Any rule change the user doesn't pick in § Open questions.
- Changing a rule early through state, memory or a child's task text. A picked change ships in this PR or in its own ticket, and the current skill stays in force until it merges.

## Today

Facts from `main` at `27fdaeb` (CW-11 merged).

| Part | Where it lives | What it does today |
|---|---|---|
| Idle check | `chief-of-staff` § Lean turns, `scripts/cos_idle_check.py` | On every run-finished turn, `status`, `where's`, and before any "nothing needs you" message: one tiny `t3_thread_read` per active child (`limit: 1`, `maxCharsPerItem: 1`) for run status and `updatedAt`. The script marks a child `full` when its last run failed, was interrupted, finished without a marker, or has been running for more than 45 minutes. |
| Sweep | `chief-of-staff` § Sweep, `scripts/cos_sweep.py` | Added by CW-11. Merged check, ready check and parent check in one command with no thread reads. Finds lost `MERGE READY` (both reviews PASS on the PR) and lost `SPEC READY` (branch moved past `specSha`). |
| Rotation chain walk | `ship-loop` § Team mode "Relays", `merge-pr` | A relay naming an approval thread other than the child's own Chief of Staff must walk back through `CHIEF OF STAFF ROTATION from <P>` links, checking a `Moved to` line in each old thread, at most 30 hops. A break stops the child with `BLOCKED:`. |
| Approval gates and head check | `ship-loop` § Phase gates and § Team mode, `merge-pr`, `scripts/merge_pr.py`, `scripts/pr_diff_delta.py` | The user approves every spec and every merge. The child checks `createdBy: "user"` on the approval. `MERGE READY` needs both reviews PASS on the current head; a head moved only by merging `main` keeps its reviews when the PR diff is unchanged. |
| Lane limits | `chief-of-staff` § Lanes | Spec 2, build 2, merge 1, overall cap 5. Waiting on the user (`awaiting-spec`, `awaiting-merge`, `blocked`) and the queued stages hold no slot. |
| Models | `chief-of-staff` § Models | Chief of Staff Sonnet 5.5 medium. Ticket helper Sonnet high. Spec child Opus 5.5. Build and merge child Sonnet 5.5 high. Implementer Sonnet. Code and security review Opus. |

### Evidence looked for

- **Idle check.** The sweep now covers the two lost-notice cases that matter most: a finished build whose reviews passed, and a pushed spec. What the sweep can't see is a child that failed, was interrupted, stopped without a marker or went quiet. Those show only in T3's run data, which needs a thread read. So the idle check's remaining job is stall detection, and it already costs the smallest read T3 allows.
- **Chain walk.** No first-hand failure found. Issue #11 listed "approval-thread chain breaks" from fathom's merged PRs and tickets, not from a failure seen here, and its own author said so. A T3 thread search for `BLOCKED: approval thread` found only that ticket-filing thread. CW-11's continuation children make the common case a direct check, and CW-14 (continuation children for restarts, answers, resumes) extends that.
- **Gates.** No report of a gate letting through something it should have stopped, or of one blocking good work. The head check's main-merge exception is new (CW-11) and has no run history yet.
- **Lane limits and models.** No queue or cost data in the repo. `.agent-team/state.json` keeps current state only, no history, so there is nothing to measure waits or spend from.

## Open questions

Each question is the user's call. My recommendation and the reason follow each one.

1. **Idle check: change it or leave it?**
   Options: (a) leave it; (b) stop running it on every run-finished turn and keep it only for `status`, `where's`, the slot-fill gate and before any "nothing needs you" message; (c) fold more of it into the sweep.
   **Recommend (a), leave it.** (c) isn't possible: run status lives only in T3 and needs a read per child. (b) saves at most four one-character reads per notice turn, and in exchange a failed or stalled child whose notice was lost waits until the user next asks for `status`. GUY-327 showed the thread skipping multi-step checks, and a stall nobody sees costs more than four small reads.

2. **Rotation chain walk: change it or leave it?**
   **Recommend leave it, and close the question.** No first-hand failure exists to fix, the common case no longer walks the chain, and CW-14 shrinks the rest. If a real `BLOCKED: approval thread ... does not descend` shows up, file a ticket with that thread.

3. **Approval gates and head check: change them or leave them?**
   **Recommend leave them.** Both gates are the user's only control over what ships, and nothing has gone wrong at either. The main-merge exception just shipped; judge it after it has run a few times.

4. **Lane limits: keep spec 2, build 2, merge 1, cap 5?**
   **Recommend keep them.** The user's review is the real limit on throughput, and waiting specs already hold no slot, so a bigger spec lane would pile up more specs to read without shipping more. Merge stays 1 so merges don't rebase on top of each other. Revisit if builds sit in `build-queued` for long; there is no data on that today.

5. **Models: keep the § Models defaults?**
   **Recommend keep them.** The spec is what the user approves, so it gets the strongest model. Builds work from an approved spec, and Opus reviews catch what a Sonnet build misses. The Chief of Staff's gates rest on the child's `createdBy: "user"` check, not on the relaying model. Nothing has shown a wrong model choice.

## Design

What the build stage does depends on the answers.

- **Every question "leave it".** Post one comment on #15 with each question, its answer and its reason (the acceptance criterion). The PR carries this spec, its as-built, index entry and release note, and no skill or script change.
- **A small "change it".** Built in this PR, under `agent-team/`. Small means a wording or number change in one section with no new script. Examples: a lane limit, a model row, dropping the idle check from run-finished turns.
- **A larger "change it".** The comment on #15 records the answer, and the PR's `Left open` asks the Chief of Staff for a ticket (its ticket helper files it). Not built here.

### Sections a change would touch

Other open work edits `agent-team/.claude/skills/chief-of-staff/SKILL.md`: PR #26 (CW-17), and the CW-12 and CW-14 specs. If every answer is "leave it", this ticket edits no skill file. Otherwise, by question:

| Question | Sections a change would edit |
|---|---|
| 1. Idle check | `chief-of-staff` § Lean turns (idle check bullet, Reports bullet), § Slot fill (gate and "Run it at the end of"), § Commands (`status` row), maybe `scripts/cos_idle_check.py` |
| 2. Chain walk | `ship-loop` § Team mode "Relays" and "Continuation tasks", `merge-pr` § Team mode |
| 3. Gates | `ship-loop` § Phase gates and § Team mode "Build stage", `merge-pr`, `scripts/merge_pr.py` |
| 4. Lane limits | `chief-of-staff` § Lanes |
| 5. Models | `chief-of-staff` § Models, maybe `.claude/agents/*.md` |

## Testing

All "leave it": nothing to test beyond the existing suite (`python3 -I -m pytest -q agent-team/scripts`). A script change from question 1 gets one table-driven test for the new rule, per `AGENTS.md` § Testing.

## Calls I made

- I recommended "leave it" on all five. With no failure, queue or cost data, I found nothing to change on evidence. Each recommendation is still yours to overturn.
- I treated "no first-hand failure" as the bar for the chain walk, following the ticket's own wording, and counted issue #11's mention as second-hand.
- I defined "small enough to build here" as one section's wording or numbers with no new script. Anything bigger becomes its own ticket.
- The answers go on #15 as one comment, posted in the build stage after you answer, not before.
- I left alone a stale-looking phrase in § Lanes ("without doubling Opus time" on the build lane, though build children run on Sonnet). It still holds for the Opus review subagents the builds start, and editing it would touch a section CW-12 and CW-14 may also edit.
