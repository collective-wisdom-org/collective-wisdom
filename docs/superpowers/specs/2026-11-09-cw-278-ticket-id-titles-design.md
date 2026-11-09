# CW-278: Show a short title next to every ticket ID in what the user reads

**Status:** Shipped
**Shipped:** in PR #279, with differences: [as-built](../as-built/2026-11-09-cw-278-ticket-id-titles-as-built.md)
**Ticket:** [#278](https://github.com/collective-wisdom-org/collective-wisdom/issues/278)

## Goal

Every ticket ID the team shows the user comes with a short plain-language title, like `CW-276: new sidebar`. A bare ID tells a person nothing about which ticket it is.

This changes only skill and role-doc markdown. No script, test or state key changes.

## Today

Facts from `main` at `304891f`.

- `chief-of-staff/SKILL.md` § Report format shows most lines with the bare ID first (`<PREFIX>-199 building (PR #180, code review pass 2)`) and says "Short lines, ticket ID first". Only the `started` lines, the `Running` links, the `Tickets` lines and the approval blocks carry a title.
- `Running` and the status tables get titles from one `list-tickets` call per turn, label `agent`, fields `id, title`. If it fails they show the ID alone.
- That call does not cover every ticket a report names:
  - The GitHub adapter's `list-tickets` lists open issues by default, so a ticket that just merged is not in it. `cos_state.py`'s `merged` op has also taken it out of `tickets`, and the `merged` map keeps only `pr` and `at`.
  - The hygiene child reports on any ticket on the tracker. Backlog tickets don't carry the `agent` label until they start.
- The hygiene child already has titles for three of its four report kinds: `fill` and `stale` from their `list-tickets` fields, duplicates from the title comparison. The drift step reads `get-ticket` without `title`.
- `pm.ranked` entries already hold `title`.
- `project-manager/reference.md` § Hygiene child keeps only child lines that start with `<PREFIX>-N ` and match a known shape, and drops the rest. A title placed after the ID breaks that filter unless the filter changes with it.
- `cos_restart.py` and `cos_route.py` print `moving:` and `cleanup:` lines with a bare ID, and the Chief of Staff copies them into the report.
- `ship-loop` markers name no ticket line of their own. Other tickets appear in `Left open or deferred`, in free-text bullets and in `BLOCKED:` lines.

## Design

### The rule

Add one paragraph to `chief-of-staff/SKILL.md` § Report format, the only place the rule is stated in full:

- Every ticket ID in a message to the user is written `<PREFIX>-N: <short title>`. The short title is a few words, about six at most, cut from the tracker title when that is long.
- The rest of the line follows after a comma: `<PREFIX>-199: Background jobs, building (PR #180, code review pass 2)`.
- A line that already has the title doesn't repeat it. This covers the `started`, `filed`, `build ready:` and `merge ready:` lines, `Running` and the status table's Ticket cell, which keep their shapes. A second mention of the same ticket on one line, such as its thread link, stays ID only.
- A script's `moving:` or `cleanup:` line is copied with the title added. The script's output doesn't change.
- A title is ticket-author text. Drop `[`, `]`, backticks and newlines from it before writing it, as the `Running` sub-lines already do for thread titles.
- Where the title comes from, first that applies:
  1. The line's own source: a child or helper report, or `pm.ranked`.
  2. The one `list-tickets` call per turn (label `agent`, fields `id, title`), the same call `Running` and status use, made only when a line needs it.
  3. For a ticket merged this turn, or asked about by `where's`, one `get-ticket` (fields `id, title`), since the open list doesn't have it.
  4. If none of these has it, or a call fails, the ID alone.
- Not covered: reply commands the user types (`"approve 210"`), PR numbers, thread titles, and anything sent to a child rather than the user.

"Short lines, ticket ID first" becomes "Short lines, ticket ID and title first", in § Report format and in `docs/agents/chief-of-staff.md`.

### Lines that change

Each line below gains the title, in the shape above.

- `chief-of-staff/SKILL.md`: the § Report format example (`blocked`, `building`, `restarted`, `approved`, `merge approved`, `merged`, `merge ready`, `Took the slot`, `unblocks`, `Done since last report`, Backlog, Cleanup), the `found by` lines, the continuation and queued lines, `Filling stopped: Backlog held`, the `found by the merged check` line in § Merged check, the `untracked` Needs you line in § Sweep, and the `Merge wait` Cleanup line.
- `chief-of-staff/status.md`: `Merged:`, `Not in my state:`, and the `where's` one-liner's `merged (#PR)`.
- `chief-of-staff/approvals.md`: the two pending-approval reminder lines.
- `chief-of-staff/no-hands.md`: the end summary's `Merged:`, `Open:` and `Waiting on you` lines. Titles for its merged tickets come from one `list-tickets` call (label `agent`, state Done, updated since the run's `startedAt`, fields `id, title`) rather than one `get-ticket` per ticket.
- `chief-of-staff/adopt.md`, `continuation.md`, `review.md`: their report lines.
- `chief-of-staff/ticket-helper.md`: the report lines named under § Observation tickets (`handoff-unavailable`, `wait-check-unreadable`, `stall`), and the helper's `Links:` and `Needs the user:` lines, which write any ticket they name with its short title. The 800-character cap stays.

### Hygiene and Backlog lines

- `project-manager/SKILL.md`: the report lines become `<PREFIX>-N: <short title>, filled: …`, `moved to Done (PR #X merged)`, `moved to In Review (PR #X open)`, `stale: …`, `may duplicate <PREFIX>-M: <short title> (commented)`, `not acted on: …` and, under Backlog, `not moved, needs: …`. The drift step's `get-ticket` adds `title` to its fields.
- `project-manager/reference.md` § Hygiene child: the filter keeps lines that start with `<PREFIX>-N` followed by a space or by `: <short title>,`, then match the same known shapes. A line with a bare ID still passes, so a child that lost a title isn't dropped.

### Child reports

`ship-loop/SKILL.md` gains one line under § Run endings: any ticket ID in a `BUILD READY`, `MERGE READY` or `BLOCKED:` message is written `<PREFIX>-N: <short title>`, with the ID alone only when the title can't be read. The markers themselves stay exactly as they are, because the Chief of Staff matches them. `Left open or deferred` in the `MERGE READY` template says the same.

## Leaves out

Per the ticket: ticket IDs in branch names, PR titles, commit messages, thread titles and script output, and how titles are written on the tracker.

Also: storing the title in the `merged` state entry, which would be a script change and a new state shape to save one small read per merge.

## Calls I made

- ⚠ A ticket that just merged costs one extra `get-ticket`. The ticket says to reuse the one `list-tickets` call and fall back to the ID, but the open list never has a merged ticket, so every `Done since last report` line would stay bare. That is the line the user reads most, and a merge happens once per ticket, so the read is cheap.
- ⚠ The hygiene child writes titles into its own report lines, and the Chief of Staff's filter accepts them. The ticket didn't ask for this, but those tickets mostly lack the `agent` label, so reuse alone would leave Cleanup bare. The child already has the titles. The title reaches the report through the child, so it is cleaned the same way as any other title and the filter still requires a known shape.
- The separator after the title is a comma, for example `CW-199: Background jobs, building`. A title with a comma in it reads slightly oddly. I preferred that to a period, which makes every status read like a new sentence.
- Lines that already carry a title keep their current shape instead of moving to `<PREFIX>-N: title`, following the ticket's "don't repeat it". So `CW-240 started: Example feature.` stays.
- A second mention of the same ticket on one line stays ID only, so `[CW-202](<thread link>)` after a titled line doesn't double the title.
- `"approve 210"` reply text stays as is, because it is what the user types.
- Titles are stripped of `[`, `]`, backticks and newlines, because they are ticket-author text going into markdown.
- The No Hands end summary uses one closed-ticket `list-tickets` instead of up to 10 `get-ticket` reads.
- No new test. `AGENTS.md` § Testing says not to test prose and copy, and the change has no script behaviour. The acceptance check is a read of every `<PREFIX>-` line in the changed files, plus the existing test suite.
- Build from this spec with no plan, as `kickoff-feature` allows for a markdown-only ticket.

## Acceptance

- No example line in the chief-of-staff docs shows a bare ticket ID where the user is the reader.
- SKILL.md § Report format states the `<PREFIX>-N: <short title>` rule once, with the fallback.
- A hygiene line with a title passes the `reference.md` filter.
- Docs checks and `python3 -I -m pytest -q agent-team/scripts` pass.
