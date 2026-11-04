# Grouped `status` layout and a risk level on every ticket and approval (design)

**Status:** Draft
**Ticket:** [CW-12](https://github.com/dbeallor/collective-wisdom/issues/12)

## Intent

When the user says `status`, the Chief of Staff answers with the full report shape: approvals, lanes, done, tickets, backlog and cleanup in one long message. The user wants a short view they can scan: tickets grouped by what each one waits on, with a risk level on every row, so they can see what needs them and approve the low-risk ones quickly. The spec and merge approval requests and their reminder lines get the same risk level up front.

## What is here today

Checked on `main` at 27fdaeb.

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Commands, row `status`, `where's <PREFIX>-N?`: run the idle check and the sweep unless this turn's full pass already read every child, then "answer from state plus the tracker, with thread links", and post the full block again for each pending approval. No layout is named, so the answer reuses § Report format.
- § Report format: `Needs you`, `Moving` by lane, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`, and the `Filling stopped:` line, which "`status` always shows".
- § State file: each ticket's `status` line already says what it waits on, e.g. `awaiting-merge since 14:05: PR #192 head 0b63161, code review PASS (pass 2), security PASS (pass 1). Waiting on the user to approve the merge.` `cos_state.py show` prints that line per ticket and prints each queue in `queuedAt` order (`queue build: …`), which is the order § Slot fill starts them.
- § Approval requests: the spec block (ends with `Touches:`) and the merge block (ends with `Risks:`), filled from `cos_brief.py` (`flag:` lines from `FLAG_WORDS`: auth, user email, money; `migrations:`; `files: N (<area> <count>, …)`) and what the Chief of Staff knows. ⚠ marks a call that changes behaviour the user might not expect. No overall risk level. Reminder lines under `Needs you` carry none either.

## Goals

- `status` (and `where's <PREFIX>-N?`) replies in a grouped layout: awaiting merge approval, merging, queued to merge, awaiting build approval, building, queued to build, other. Empty groups drop out. Each group header shows its ticket count. Queued groups list tickets in start order.
- Each row: ticket ID and title, a risk level (`Low`, `Medium`, `High`) with a few-word reason, and one detail line that names the user's action when there is one.
- The skill defines how risk is decided from inputs the Chief of Staff already reads, with High winning ties and fixed file-count thresholds.
- The spec block, the merge block and each reminder line show the risk level and reason on their first line.
- The risk level is kept in the ticket's `status` line, so `status` shows it with no extra reads.
- The skill says the risk level never approves a ticket or skips, shortens or changes any gate.

## Non-goals

- The report format for run-finished and other turns. Only the approval blocks and reminder lines gain the risk line; the rest of § Report format is unchanged.
- What the idle check, the sweep (merged, ready and parent checks) and slot fill do. `status` still runs them first.
- New fields in `cos_state.py`, new output from `cos_brief.py`, or any script change. No tests change.
- Any rule that makes approval automatic or skippable for Low risk.
- § State file. The rule that keeps the risk in the `status` line lives in § Approval requests, so the § State file text is untouched.

## Design

All edits are in `agent-team/.claude/skills/chief-of-staff/SKILL.md`, in three places only, so PR #26 (CW-17, which also edits this file) can rebase cleanly. Its hunks (checked at the time of writing) add two § Commands rows after `a change to how the team works`, a § Guardrails line and edits elsewhere; none touch the `status` row, § Approval requests or § Report format.

1. § Commands: the `status`, `where's <PREFIX>-N?` row.
2. § Approval requests: the two block templates, the reminder template, and a new `### Risk level` subsection at the end of the section.
3. § Report format: the `Needs you` example (block first line and reminder line) and a new `### Status layout` subsection at the end of the section.

No other section, script, test or doc changes. The release note, index entry and as-built ship with the PR as usual.

### 1. § Commands, `status` row

The row keeps the idle check and sweep sentence and the "post the full block again for each pending approval" sentence. "answer from state plus the tracker, with thread links" becomes "answer in § Report format "Status layout"". The queued-ticket bullet further down (`status`: say `approved, waiting for a build slot`) stays; that text becomes the row's detail line.

### 2. § Approval requests

**Block first lines.** The risk goes on the first line, after the title, before any list:

```
<PREFIX>-210 spec ready: Example feature. Risk: Low (docs only, 3 Builds bullets)
```

```
<PREFIX>-197 merge ready: <PR title>. Risk: High (touches auth)
```

`Touches:` and `Risks:` stay where and as they are.

**Reminder lines** start with the level:

```
- Low (docs only, 2 files): <PREFIX>-197 merge still waiting on you: <PR URL>, head <short SHA>. "approve 197" or "changes 197: …"
```

This is the one place a report line does not start with the ticket ID; the ticket asks for the level first so the user can pick out low-risk ones.

**New `### Risk level` subsection.** Text to this effect:

Rate each spec and merge when you build its block, from what you already have. No new tool calls.

| Level | When |
|---|---|
| High | It touches data, money, auth, user email or migrations: a `migrations:` clash, a `flag:` line, a `Touches` entry other than "none of these", or anything else you know touches them. Or the child made a call that changes behaviour the user might not expect (a ⚠ line). |
| Medium | None of the High reasons, and either it is not small (below), or it changes how the team itself works: gates, lanes, commands, skills, `scripts/`, `docs/agents/`, `AGENTS.md`. |
| Low | None of the above: small, and mostly docs or prose. |

Small means:

- A merge: 5 files or fewer in `cos_brief.py pr`'s `files:` count. 6 or more is large.
- A spec (no diff yet): 4 `Builds` bullets or fewer. 5 or 6 is large. Rate it from `Touches`, `Calls the child made` and the `Builds` list.

When two levels fit, take the higher one. Write the reason in a few words next to the level: `Low (docs only, 2 files)`, `Medium (changes slot fill, 4 files)`, `High (touches auth)`, `High (⚠ new default for existing users)`.

Keep the rating in the ticket's `status` line: end the line written with the `awaiting-spec` or `awaiting-merge` stage op with `Risk: <Level> (<reason>).`, and carry that tail unchanged into every later `status` line for the ticket until a new block replaces it (a merge rating replaces the spec rating). A ticket never rated (spec stage before its first `SPEC READY`, queued or blocked before then) shows `Risk: not rated yet`. Never guess one.

The risk level informs the user and nothing else. It never approves a ticket, skips or shortens a gate or a review, or changes who may approve. Every ticket still needs the user's `approve N`, whatever its level.

### 3. § Report format, `### Status layout`

**Format: one small markdown table per group, under a bold header with the count.** The user scans down one column for the ticket, one for the risk, and reads the next action in the third, without reading prose. Separate tables (rather than one table with a group column) keep the group order and counts visible as headers and don't repeat the group name on every row. Chat clients that render GitHub-flavoured markdown (T3 Code does) show them as tables; unrendered, they still read line by line.

```
**Awaiting merge approval (1)**

| Ticket | Risk | Next |
|---|---|---|
| **CW-197** CSV export | High (touches auth) | PR #180, reviews PASS. Reply `approve 197` or `changes 197: …`. <thread link> |

**Building (2)**

| Ticket | Risk | Next |
|---|---|---|
| **CW-199** Background jobs | Medium (changes slot fill, 4 Builds bullets) | PR #181, code review pass 2. <thread link> |
| **CW-154** Retry button | Low (docs only, 2 Builds bullets) | Restarted: stalled after code review PASS. <thread link> |

**Queued to build (1)**

| Ticket | Risk | Next |
|---|---|---|
| **CW-238** Export filters | Low (prose only, 3 Builds bullets) | Approved, waiting for a build slot. <thread link> |

**Other (1)**

| Ticket | Risk | Next |
|---|---|---|
| **CW-240** Example feature | not rated yet | Spec stage since 14:05, no SPEC READY yet. <thread link> |

Filling stopped: lanes full.
```

Groups, in this order, by stage:

| Group | Stages |
|---|---|
| Awaiting merge approval | `awaiting-merge` |
| Merging | `merge` |
| Queued to merge | `merge-queued`, in `cos_state.py show`'s `queue merge:` order |
| Awaiting build approval | `awaiting-spec` |
| Building | `build` |
| Queued to build | `build-queued`, in the `queue build:` order |
| Other | `spec`, `spec-queued` (in `queue spec:` order), `blocked` |

Rules:

- Empty groups drop out. The header count is the number of rows.
- Risk and detail come from the ticket's `status` line in state. The detail line is the status line shortened to what changed or what the user must do, and names the reply when the user has an action (`Reply "approve N"`, or for a blocked ticket the question to answer). An `other` row says why it is there (`spec stage`, `blocked: <reason>`, `changes requested, waiting for a spec slot`).
- Titles come from the tracker read `status` already makes today. If that read fails, show the ID alone.
- Anything this turn's idle check or sweep found goes in that ticket's detail line (`merge ready, found by the sweep`). A ticket the sweep found merged leaves state, so it gets one line below the tables: `Merged: CW-190 (#178)`.
- After the tables: the `Filling stopped:` line (`status` always shows it), then the full block for each pending approval, as § Approval requests says, each with its risk on the first line.
- No other § Report format section (`Moving`, `Done since last report`, `Tickets`, `Backlog`, `Cleanup`) appears in a `status` answer. A Cleanup item that came up waits for the next report.
- `where's <PREFIX>-N?` uses the same layout with only that ticket's group and row, plus its full block if it waits on an approval.

## Verification

Prose-only change to one skill file. No script or test changes, so the test suite should pass unchanged (`python3 -I -m pytest -q agent-team/scripts`, `shellcheck`). Manual check in the PR: every acceptance line in the ticket maps to text in the diff, and `git diff` touches only the three named sections of the skill (plus closeout docs).

## Calls I made (surprising first)

- ⚠ The ticket lists both an "awaiting build approval" group and "awaiting spec approval" under `other`. There is no separate stage for those: approving a spec (`awaiting-spec`) is what starts the build. I mapped `awaiting-spec` to **Awaiting build approval**, so that group isn't always empty. Under `other` go `spec`, `spec-queued` and `blocked`.
- One file-count cut for merges: 5 files or fewer is small, 6 or more is large. Two separate numbers would leave diffs of, say, 8 files fitting neither Low nor Medium. A small merge must also be mostly docs or prose to be Low.
- For a spec, size is the `Builds` list: 4 bullets or fewer is small, 5 or 6 (the cap) is large.
- A `Touches` entry other than "none of these" makes a spec High. This follows the ticket's "touches data" rule.
- In collective-wisdom almost every PR changes skills or scripts, so most tickets here will rate Medium or higher. That is the ticket's rule applied as written.
- The format is one markdown table per group with a bold header and count, ticket ID in bold. Thread links go at the end of the Next cell.
- Reminder lines start with the risk, not the ticket ID. This is the one exception to "ticket ID first" in § Report format.
- Risk carries forward in the `status` line until a new rating replaces it, and the rule for that sits in § Approval requests, not § State file, to keep the edit inside the three sections named in Design. PR #26 (CW-17) adds two rows near the end of the § Commands table and one § Guardrails line; none of its hunks overlap these three edits.
- Merges found by the sweep during `status` show as one `Merged:` line below the tables, since they no longer have a stage. Other report sections (Cleanup, Backlog, Tickets) don't appear in a `status` answer.
- `where's <PREFIX>-N?` uses the same layout cut down to one row.
