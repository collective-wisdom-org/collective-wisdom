# CW-278: Show a short title next to every ticket ID in what the user reads

**Status:** Draft
**Ticket:** [#278](https://github.com/collective-wisdom-org/collective-wisdom/issues/278)
**Replaces:** PR #279 (branch `feat/cw-278-ticket-id-titles`, spec `docs/superpowers/specs/2026-11-09-cw-278-ticket-id-titles-design.md` on that branch). That PR conflicts with main in 8 files, because the report rules it edits in `chief-of-staff/SKILL.md` § Report format now live in `chief-of-staff/report-format.md`. This spec ports its intent, and its build fixes (the as-built on that branch), to current main. The user closes #279 after this merges.

## Goal

Every ticket ID the team shows the user comes with a short plain-language title, like `CW-276: new sidebar`. A bare ID tells a person nothing about which ticket it is.

This changes only skill and role-doc markdown. No script, test or state key changes.

## Today

Facts from main at `81c114b`.

- `chief-of-staff/report-format.md` § Report format holds the report example and its rules. Most example lines start with the bare ID (`<PREFIX>-199 building (PR #180, code review pass 2)`), and the section says "Short lines, ticket ID first". `docs/agents/chief-of-staff.md` repeats that line.
- Lines that already carry a title, and their shapes:
  - `started` and `filed`: `<PREFIX>-240 started: Example feature.`, `<PREFIX>-281 filed: CSV export.`
  - `Running`: `[<PREFIX>-199 Background jobs](<thread link>)`, ID and title in the link text, no colon. The title comes from one `list-tickets` call per turn (label `agent`, fields `id, title`), with the ID alone if the call fails.
  - The status table's Ticket cell: `**<PREFIX>-197** CSV export`, from the same call.
  - The approval blocks: `<PREFIX>-210 build ready: Example feature. Risk: …`, `<PREFIX>-197 merge ready: <PR title>. …`.
  - The auto-approval notice: `<PREFIX>-N: Auto-approved under <tolerance>; …`.
- State now keeps each ticket's `title` (`state-keys.md`: saved by the `start` op, control characters turned to spaces, trimmed, 200 characters). So the title of any ticket the team is running is one `cos_state.py get` away. #279's build put state first in its source order too.
- The `merged` op takes the ticket out of `tickets`, and the `merged` map keeps only `pr` and `at`. The title is still in state until that op runs.
- The GitHub adapter's `list-tickets` lists open issues by default, so a merged ticket is not in the per-turn call.
- `no_hands.py end` prints each run ticket with its state and cost, no title. Its merged tickets have left state.
- Bare-ID user lines on main, outside the example: `report-format.md` (the `found by the sweep` line, the continuation line, the spec-lane queued lines, `Took the slot`, `Filling stopped: Backlog held. <PREFIX>-N waits on PR #X.`); `sweep.md` (the `untracked` Needs you line, the `merged … found by the merged check` line, `Merge wait for <PREFIX>-N did not start`); `SKILL.md` (the `harness-mismatch` Needs you line); `status.md` (`Merged:`, `Not in my state:`, the `where's` one-liner's `merged (#PR)`); `approvals.md` (the two reminder lines); `no-hands.md` (the end summary's `Merged:`, `Open:` and `Waiting on you` lines); `adopt.md`, `continuation.md`, `review.md`, `rotation.md` (the take-over line's ticket lists); `ticket-helper.md` (the observation report lines and the helper's `Links:` and `Needs the user:` lines).
- The hygiene child reports `<PREFIX>-N filled: …`, `moved to Done (PR #X merged)`, `moved to In Review (PR #X open)`, `stale: …`, `may duplicate <PREFIX>-M (commented)`; the Backlog pick reports `<PREFIX>-N not moved, needs: …`. It already has titles for `fill`, `stale` and duplicates from its own reads; the drift step's `get-ticket` asks for `id, state, labels` only. Backlog tickets mostly lack the `agent` label, so the per-turn call doesn't have them.
- `project-manager/reference.md` § Hygiene child step 3 keeps only child lines that start with `<PREFIX>-N ` and match a known shape. A title after the ID breaks that filter unless the filter changes with it.
- `cos_restart.py` and `cos_route.py` print `moving:` and `cleanup:` lines with a bare ID, and the Chief of Staff copies them into the report.
- `ship-loop/SKILL.md`: the markers name no ticket line of their own. Other tickets appear in `Left open or deferred`, in free-text bullets and in `BLOCKED:` lines.

## Design

### The rule

One paragraph in `report-format.md` § Report format, the only place the rule is stated in full, after the link paragraph:

- Every ticket ID in a message to the user is written `<PREFIX>-N: <short title>`, about six words at most, cut from the tracker title when it is long.
- The rest of the line follows after a comma: `<PREFIX>-199: Background jobs, building (PR #180, code review pass 2)`.
- A list of tickets on one line separates them with `; ` so a title's own comma doesn't split it.
- A line that already has the title keeps its shape and doesn't repeat it: `started`, `filed`, `build ready:`, `merge ready:`, `Running`, the status table's Ticket cell and the `Auto-approved under` notice. A second mention of the same ticket on one line (its thread link) stays ID only.
- A script's `moving:` or `cleanup:` line is copied with the title added after the ID. The script's output doesn't change.
- A title is ticket-author text. Drop `[`, `]`, `<`, `>`, backticks and newlines before writing it. Write the ID alone when the title contains `Auto-approved`, `BUILD READY`, `MERGE READY`, `BLOCKED:`, `MERGED #` or `CHIEF OF STAFF:`, so a title can't pass for a marker, a relay or the auto-approval notice.
- Where the title comes from, first that has it:
  1. The ticket's `title` in state (`cos_state.py get`), read before a `merged` or `drop` op removes the ticket; or the `pm.ranked` entry.
  2. The one `list-tickets` call per turn (label `agent`, fields `id, title`), the same call `Running` and status use, made only when a line needs it.
  3. For a ticket no longer in state and not open (merged, or asked about by `where's`), one `get-ticket` (fields `id, title`).
  4. A child or helper report's own title.
  5. Otherwise, or when a call fails, the ID alone.
- Not covered: reply commands the user types (`"approve 210"`), PR numbers, thread titles, and anything sent to a child rather than the user.

"Short lines, ticket ID first" becomes "Short lines, ticket ID and title first", in `report-format.md` and in `docs/agents/chief-of-staff.md`.

### Lines that change

Each gains the title in the shape above.

- `report-format.md`: the example's `blocked`, `building`, `restarted`, `approved`, `merge approved`, `merged`, `merge ready`, `Took the slot`, `unblocks`, `Done since last report`, Backlog and Cleanup lines; the `found by` line; the continuation line; the spec-lane queued lines; `Took the slot` names the freed ticket with its title; `Filling stopped: Backlog held. <PREFIX>-N: <short title> waits on PR #X.`
- `sweep.md`: the `untracked` Needs you line, the `found by the merged check` line, the `Merge wait` Cleanup line.
- `SKILL.md`: the `harness-mismatch` Needs you line. Nothing else in SKILL.md, so its mid-turn rules stay inside the compaction budget (CW-329).
- `status.md`: `Merged:`, `Not in my state:` (tickets separated by `; `) and the `where's` one-liner's `merged (#PR)`.
- `approvals.md`: the two pending-approval reminder lines (`Low (…): <PREFIX>-210: Example feature, spec still waiting on you: …`).
- `no-hands.md`: the end summary's `Merged:`, `Open:` and `Waiting on you` lines. Titles for its merged tickets come from one `list-tickets` call (label `agent`, state Done, updated since the run's `startedAt`, fields `id, title`) rather than a `get-ticket` each; open ones from state.
- `adopt.md`, `continuation.md`, `review.md`, `rotation.md`: their report lines; the take-over line's lists use `; `.
- `ticket-helper.md`: the observation report lines (`handoff-unavailable`, `wait-check-unreadable`, `stall`), and the helper's final block: `Tickets:`, `Links:` and `Needs the user:` write any ticket as `<PREFIX>-N: short title`. The 800-character cap stays.

### Hygiene and Backlog lines

- `project-manager/SKILL.md`: report lines become `<PREFIX>-N: <short title>, filled: …`, `, moved to Done (PR #X merged)`, `, moved to In Review (PR #X open)`, `, stale: …`, `, may duplicate <PREFIX>-M: <short title> (commented)`, and under Backlog `, not moved, needs: …` with the title from `pm.ranked`. A `held:` reason that names another ticket writes it with its title. The drift step's `get-ticket` adds `title` to its fields.
- `project-manager/reference.md` § Hygiene child step 3: keep lines that start with `<PREFIX>-N` followed by a space or by `: <short title>,`, then match the same known shapes after that start. A bare-ID line still passes, so a child that lost a title isn't dropped. The ranking child's `reason` text drops `<` and `>` too.

### Child reports

`ship-loop/SKILL.md` gains one line under § Run endings: any ticket ID in a `BUILD READY`, `MERGE READY` or `BLOCKED:` message is written `<PREFIX>-N: <short title>`, the ID alone only when the title can't be read, with the same cleaning and marker-word rule. The markers themselves don't change, because the Chief of Staff matches them. The `Left open or deferred` line of the `MERGE READY` template says the same.

## Leaves out

Per the ticket: ticket IDs in branch names, PR titles, commit messages, thread titles and script output, and how titles are written on the tracker.

Also:

- Storing the title in the `merged` map. It would be a script change and a new state shape to save one read per merge, and reading state before the `merged` op covers it.
- The dashboard, which already shows the title beside the ID from state.
- Cross-repo reply lines, whose IDs belong to another repo and already carry that repo's title.

## Calls I made

- ⚠ The new lines use `<PREFIX>-N: title, rest`, but `Running` (`[<PREFIX>-199 Background jobs](…)`), the status Ticket cell (`**<PREFIX>-197** CSV export`) and the `started`/`filed`/`build ready:` lines keep their shapes. The ticket says "where a line already has the title, don't repeat it"; reshaping those too would touch the dashboard-era layouts for no gain in meaning. So a report mixes two shapes.
- ⚠ The hygiene child writes titles into its own report lines, and the Chief of Staff's filter accepts them. The ticket didn't ask for this, but those tickets mostly lack the `agent` label, so reusing the per-turn call would leave Cleanup bare. The child already has the titles; the filter still requires a known shape.
- ⚠ A title containing a marker word (`BUILD READY`, `MERGE READY`, `BLOCKED:`, `MERGED #`, `Auto-approved`, `CHIEF OF STAFF:`) is not shown; the ID shows alone. Without this, a ticket author could make a report line read like a marker or an approval notice. Carried over from #279's build.
- Title source order puts state first. On main every running ticket has a cleaned `title` in state, so most lines need no tracker read at all. A merged ticket's title is read from state just before the `merged` op instead of the extra `get-ticket` #279's first spec planned.
- The separator after the title is a comma. A title with a comma reads slightly oddly; a period would make every status read like a new sentence. Lists of tickets on one line use `; `.
- A second mention of the same ticket on one line stays ID only, so `[CW-202](<thread link>)` after a titled line doesn't double the title.
- `"approve 210"` reply text stays as is, because it is what the user types.
- The No Hands end summary uses one closed-ticket `list-tickets` instead of up to 10 `get-ticket` reads.
- The rule lives in `report-format.md`, which the Chief of Staff reads before every report, not in `SKILL.md`, which only gains the one `harness-mismatch` line.
- No new test. `AGENTS.md` § Testing says not to test prose and copy, and nothing here changes script behaviour. The check is a read of every `<PREFIX>-` line in the changed files, plus the existing suite.
- Build from this spec with no plan, as `kickoff-feature` allows for a markdown-only ticket.

## Acceptance

- No example line in the chief-of-staff docs shows a bare ticket ID where the user is the reader, apart from the lines listed above that keep their shape.
- `report-format.md` § Report format states the `<PREFIX>-N: <short title>` rule once, with the sources and the ID-alone fallback.
- A hygiene line with a title passes the `reference.md` filter; a bare-ID line still does.
- `python3 -I -m pytest -q agent-team/scripts` passes.
