# CW-256: Record a Chief of Staff run and a ship-loop child on Cursor in T3 Code

**Status:** Draft
**Ticket:** [#256](https://github.com/collective-wisdom-org/collective-wisdom/issues/256)

## Goal

Find out, by running it, whether the agent team works when the Chief of Staff and its ship-loop child are Cursor threads in T3 Code. Write down what happened in `docs/compatibility.md` well enough that someone can do the run again, and file one ticket for each thing that broke.

## The problem with running it from here

A ship-loop child cannot start a Cursor thread. Its task forbids `t3_thread_launch`, `create_threads` and `delegate_task`, and it cannot type into a new T3 thread. CW-252 hit the same wall. So the run itself has to be started by the Chief of Staff (which may launch threads) or by the user. Everything around the run (the trial repo, the procedure, reading the transcripts, checking the dashboard, filing tickets, updating the doc) the child does itself.

The build therefore stops once in the middle with `BLOCKED: Cursor run needed` and a short list of steps, and picks up again when the Chief of Staff relays that the run is done and gives the thread ids.

## Where the run happens

Not in this repo. collective-wisdom already has a running Chief of Staff (Claude Code) and one `.agent-team/state.json` on the root checkout. A second Chief of Staff on the same repo would fight over that state and over the Backlog. The run uses a throwaway private repo instead:

- `dbeallor/cw-cursor-trial` on GitHub, private, tracker `github`, prefix `CT`.
- A local clone at `~/Documents/cw-cursor-trial`, added as a T3 Code project.
- One `README.md` and one small ticket: issue "Add a one-line project description to README.md", type Improvement. Small enough that the spec and the build are a few lines each, so the run tests the team's moving parts and not Cursor's coding.

The Cursor Chief of Staff runs `set up this repo` there itself. That writes the trial repo's `docs/agents/project.md` and is a check in its own right: it is the first team skill the thread has to load and follow.

## Build steps

1. **Trial repo.** Create `dbeallor/cw-cursor-trial` (private) with `~/.collective-wisdom/scripts/gh.sh repo create`, push a one-line `README.md` from a clone at `~/Documents/cw-cursor-trial`, and file the ticket above with `gh.sh issue create`. Nothing else goes in the repo: no `project.md`, so the Cursor thread has to set it up.
2. **Procedure.** Add a `## Recording a run` section to `docs/compatibility.md` with the steps below, written so they work for any harness column (Codex and Antigravity runs can reuse it later). Commit and push.
3. **Hand-off.** Stop with `BLOCKED: Cursor run needed` and the steps for whoever starts the run:
   1. Add `~/Documents/cw-cursor-trial` as a T3 Code project.
   2. In that project, start a new thread with the Cursor provider and send `set up this repo`. Answer its setup questions with the defaults it offers, tracker GitHub.
   3. In the same thread send `start the team`, then take `CT-1` through: approve the spec and the merge from that thread when it asks.
   4. While it runs, open the dashboard for the trial repo and note whether the Chief of Staff tab shows the Cursor thread, its state and its link.
   5. Reply here with `CHIEF OF STAFF:` and the Cursor Chief of Staff thread id, the child thread id(s), how far the ticket got, and what the dashboard showed.
4. **Read the run.** With `t3_thread_read`, read the Cursor Chief of Staff thread and each child thread. For each cell below, decide works, partial or not supported from what the threads show: a quoted tool call or reply, not a guess.
5. **Dashboard.** Run the dashboard API for the trial repo (`agent-team/scripts/dashboard/server.ts`, its `/api` route) and record what `chief` holds: `state`, `threadLink`, and whether `gantt` is empty (expected, G9).
6. **Tickets.** For each failure, file one ticket in collective-wisdom with the `write-ticket` skill, linking back to its cell and gap number. Do not fix anything.
7. **Doc.** Update the Cursor column of `docs/compatibility.md`, replace G3, fill in the run record, and open the PR.

## What the run checks

| Cell | Works when |
|---|---|
| Team skills load | The Cursor thread follows `set up this repo` and `start the team` from the installed `chief-of-staff` skill: it reads the skill's files, not a guess from the name. |
| Chief of Staff thread | It writes `.agent-team/state.json` in the trial root checkout, launches a child thread for `CT-1`, relays `BUILD READY` and `MERGE READY` to the user, and runs `cos_approve_pr.py` before the merge relay. |
| Ship loop child threads | The child (whatever provider the Chief of Staff gives it) runs ship-loop to `MERGED #N`: spec pushed, PR opened, code and security review comments posted with `Verdict: PASS`, `merge_pr.py` merges. |
| Local dashboard (the "rest untested" half) | The Chief of Staff tab shows the Cursor thread's state and a working thread link. Gantt rows and spend stay missing under G9. |

The child thread's provider is recorded as the Chief of Staff chose it. If the Cursor Chief of Staff starts a Claude Code child, the Ship loop cell records that and says the Cursor child is still untested, and a ticket covers it.

Cells the run touches but the ticket does not ask about (Install G1, Subagents G4, Security review G11) get a note in the run record if the run shows something, and keep their current value unless the run settles them. G1 is likely settled: a Cursor thread that follows the rule file's text is the read CW-252 could not record.

## Run record

`docs/compatibility.md` gets a `## Runs` section with one entry per recorded run: date, harness, trial repo, the thread ids, how far the ticket got, and one line per cell with what was seen. The legend's sentence "A run that no doc records is named in a note" then has a place to point to. The Cursor cells and G3 link to this entry.

## Calls I made

- **The build stops halfway for someone to start the Cursor thread.** A child cannot start one, so the run has to be launched by the Chief of Staff or by you. That `BLOCKED:` is planned; it is not a failure.
- **A new private repo `dbeallor/cw-cursor-trial`, created by the child.** Running a second Chief of Staff in collective-wisdom would clash with the one already running. Approving this spec approves creating that repo. It is left in place after the run so a later run can reuse it; deleting it is up to you.
- **The trial ticket is filed by the child, not the Cursor Chief of Staff.** Filing tickets is a separate skill; the point is the run, and a ready ticket keeps it short.
- **You approve the trial ticket's spec and merge in the Cursor Chief of Staff thread.** That is the real path, so it is part of what the run tests. The trial repo uses `strict` approval, so nothing is auto-approved.
- **The child keeps its default provider choice.** The run does not tell the Cursor Chief of Staff which provider to give the child. Whatever it picks is recorded.
- **One ticket per failure, filed in collective-wisdom**, not in the trial repo.
- **A `## Recording a run` procedure and a `## Runs` record** are added to `docs/compatibility.md`, written to fit any harness column.
- **The trial clone lives at `~/Documents/cw-cursor-trial`**, outside any worktree. It holds no data directories and no docker.

## Leaves out

- Fixing any failure (each gets its own ticket).
- Codex and Antigravity runs.
- The Subagents cell beyond a note: that is #255.
- Deleting the trial repo after the run.
- Any change to skills, scripts or `install.sh`.

## Touches

None of: data, money, auth, user email, migrations. It creates one private GitHub repo under your account.
