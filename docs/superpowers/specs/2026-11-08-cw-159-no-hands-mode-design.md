# CW-159: No Hands mode, working the Backlog with no approvals

**Status:** Shipped
**Shipped:** in PR #215, with differences: [as-built](../as-built/2026-11-08-cw-159-no-hands-mode-as-built.md)
**Ticket:** [#159](https://github.com/collective-wisdom-org/collective-wisdom/issues/159)
**Related:** the `Approval risk tolerance` setting and `approvals.md` § Auto-approval; `kill-switch.md`; `project-manager` § Backlog pick.

## Goal

The user can start a **No Hands run**: the Chief of Staff approves specs and merges itself, at any risk level, and keeps starting tickets from Todo and the Backlog until nothing is left to start and everything it started has merged or stopped. Every review, CI check and merge gate still runs. The run stops on its own at a ticket cap, a cost cap, a blocked ticket, or `stop everything`, reports why, and never starts again without the user.

## Today

Facts from `main` at `23b0002`.

- `project_config.approval_setting()` reads the `Approval risk tolerance` row of `project.md` as committed on `origin/<target>`; a missing row, an unknown value or a failed read is `strict`. `approval_policy.decide(tolerance, level)` auto-approves only levels in `AUTO_UP_TO[tolerance]`; High and unrated always ask.
- `approval_policy.py auto <PREFIX>-N spec` (Chief of Staff) and `check <Level>` (child) decide specs. `cos_approve_pr.py --auto` decides merges through `auto_gate`: the rule, then no renamed file, fewer than 100 files, no file on the approval path (`on_approval_path`: every dot-directory and dot-file, all of `scripts/` and `docs/agents/`, the templates, `install.sh`, `tag-release.sh`, every `AGENTS.md`/`CLAUDE.md`), no `flag:` path or migration file (`cos_brief.py`), and no unreviewed conflict-resolution note.
- `approvals.md` § Observation tickets: a ticket filed from the Chief of Staff's own observation is never auto-approved.
- In collective-wisdom almost every ticket changes `agent-team/scripts/` or `agent-team/.claude/`, so `permissive` auto-approves almost no merge here.
- The slot fill (`cos_tick.py`, `LIMITS` and `CAP`) prints one `start-todo` per free spec slot. Todo goes first, then `project-manager` § Backlog pick until `cos_rank.py dry` says the Backlog is dry. Specs that reach `awaiting-build` hold no slot, so the spec lane keeps starting tickets while approvals wait.
- Stops: `stop everything` cancels running children, blocks their tickets with note `stopped by the user` and sets `paused`; `resume` clears it and relays those tickets back. `cos_restart.py` restarts a stuck child once per stage, then blocks it. A rate-limited ticket resumes up to 3 times, then stays blocked.
- `agent_usage.py --ticket <PREFIX>-N` prints a ticket's API-equivalent `cost:` line; exit 2 means unknown.
- `cos_state.py` allows a fixed set of top-level keys (`TOP`); `state-keys.md` forbids `policy`, `settings` or `rules` keys.

## Design

### Two locks: a committed setting and the user's own command

A run needs both:

1. **The setting**, three new rows in `project.md` § Identity next to the tolerance, read from `origin/<target>` as committed (never a working tree), like the tolerance:

   | Key | Value |
   |---|---|
   | No Hands (`off` or `on`) | `off`. Whether the user may start a No Hands run |
   | No Hands ticket cap | `10`. Tickets one run may start |
   | No Hands cost cap (USD) | `200`. API-equivalent spend of the run's tickets, from `agent_usage.py` |

   A missing row, an unknown value, a cap that is not a positive whole number, or a failed read reads as `off`. An app on an older `project.md` has no row, so it reads as `off`.

2. **The command** `no hands` from the user in the Chief of Staff thread. `no hands off` ends the run.

The setting says the mode is allowed and holds its limits. The command starts one run, with a beginning and an end the caps count from. Turning the setting on is a `project.md` change, which is on the hands path (below), so a No Hands run can never turn itself on or raise its caps; it takes a PR the user approves.

### Run record in state

A new top-level state key `noHands`, written only by the new script `no_hands.py` (through `cos_state.py`), holds the current or last run:

```json
"noHands": {"startedAt": "…", "itemId": "<the user's no hands message>", "started": ["CW-210"],
            "drain": null, "endedAt": null, "endReason": null}
```

It is a run record, not a rule: it holds when the run began, which message began it, which tickets it started and how it ended. `state-keys.md` describes it. `cos_state.py`'s `start` op appends the ticket to `started` while a run is active (not ended), so the count cannot be skipped.

### `no_hands.py`

New script, Chief of Staff only, run from the root checkout.

- `start --thread <id>`: needs the setting `on`, no active run, and `cos_user_check.py latest <thread>` with words `no hands` exit 0. Writes a fresh `noHands` with that item id. Prints `no-hands: started (cap N tickets, $C)` or `no-hands: refused (<why>)`.
- `check`: prints exactly one of `no-hands: off`, `no-hands: on N/cap $X/$C`, `no-hands: drain <reason> N/cap $X/$C`, `no-hands: stop cost-cap $X/$C`, `no-hands: stop <why>` (setting turned off, cost unknown, the start message no longer verifies). Cost is the sum of `agent_usage.py --ticket` over `started`; a ticket whose cost is unknown makes the run stop (`cost unknown`), since an unmeasured run cannot be held to its cap.
- `drain <reason>`: sets `drain` (no new starts; approvals stay automatic).
- `end <reason>`: sets `endedAt` and `endReason`, and prints the run summary lines (below).
- `active()`, imported by the approval scripts: true only when the setting is `on`, a run has started and not ended, the cost is under the cap, and `cos_user_check.py item <chiefThreadId> <itemId>` with words `no hands` still says `user`. So a `noHands` key written into state by anything other than the user's command approves nothing.

### What No Hands approves

While `no_hands.active()` is true:

- **Specs** are auto-approved at any level, High and unrated included, and observation tickets too. One exception: a spec whose `Builds` change a file on the **hands path** still asks the user (the Chief of Staff's reading, as today with the approval path; the merge check enforces it).
- **Merges** are auto-approved at any level, observation tickets included, unless the PR:
  - changes a file on the hands path,
  - renames a file, or has 100 files or more (too hard to check),
  - has a migration file or a `flag:` path (money, auth, user email), or
  - carries an unreviewed conflict-resolution note.

  Those still wait for the user's `approve N`, and the run goes on with other tickets.

**The hands path** is a short list in `approval_policy.py` (`HANDS_PATH`), matched like the approval path (with or without `agent-team/`, ignoring case): the files that decide approvals, the mode and its caps, the merge and review gates, and the always-on instructions:

- `docs/agents/project.md`, `templates/project.md`, `install.sh`, `tag-release.sh`
- `.github/` and `CODEOWNERS` at any depth (CI and required reviewers)
- `AGENTS.md`, `CLAUDE.md` and their override and local forms at any depth
- skills: `.claude/skills/chief-of-staff/`, `ship-loop/`, `open-pr/`, `security-review/`, `merge-pr/`
- role docs: `docs/agents/security-review.md`, `code-review.md`, `chief-of-staff.md`, `github-auth.md`; the reviewer agent files `.claude/agents/code-reviewer.md` and `security-reviewer.md`
- scripts: `approval_policy.py`, `no_hands.py`, `cos_approve_pr.py`, `cos_user_check.py`, `merge_pr.py`, `review_gate.py`, `review_scope.py`, `ci_review.py`, `wait-for-ci.sh`, `gh.sh`, `cos_brief.py`, `cos_state.py`, `cos_tick.py`, `cos_route.py`, `cos_head_check.py`, `agent_usage.py`, `prices.json`, `project_config.py`, `user_config.py`, `app_root.py`, each with its `test_<name>.py`

A test computes the local imports of every hands-path script and fails if one is not on the list, so a gate cannot be moved into an unlisted helper. Everything else on today's approval path (most of `scripts/`, the other skills and role docs, other dot-directories) can be auto-approved during a run, which is what makes the mode useful in this repo.

With the mode off, or no active run, nothing changes: `decide`, the approval path and the observation rule work as today under all three tolerances.

### The child's check

The auto spec relay under No Hands reads `CHIEF OF STAFF: auto-approved the spec under No Hands.` The Chief of Staff's notice says `Auto-approved under No Hands; …`. `ship-loop` § Approvals accepts that notice like the tolerance one, and the child runs `approval_policy.py check no-hands` (new argument), which exits 0 only when `no_hands.active()`. Under No Hands the child stops with `BLOCKED:` if its own spec changes a hands-path file (in place of the approval-path rule). Merge relays are unchanged: `cos_approve_pr.py --auto` verified the merge before the relay.

### How a run goes and ends

The tick runs `no_hands.py check` while a run is active (a new `run` line from `cos_tick.py`), and the slot fill obeys it:

| `check` says | Slot fill | Approvals | What the Chief of Staff does |
|---|---|---|---|
| `on` | as today | No Hands | nothing |
| `drain <reason>` | no `start-todo` | No Hands | when no ticket of the run is in `spec`, `build`, `merge` or a queued stage: `end <reason>`, set `paused` |
| `stop <why>` | none | the tolerance | kill-switch steps 1 to 4 with note `stopped by No Hands: <why>`, then `end <why>` |
| `off` | as today | the tolerance | nothing |

What puts a run into each state:

- **Ticket cap.** `started` reaches the cap: `drain ticket-cap`. Tickets already started finish.
- **Blocked ticket.** A child of the run reports `BLOCKED:` (not `rate limited`), or `cos_restart.py` blocks a stuck child after its one restart: `drain blocked <PREFIX>-N`. The blocked ticket waits for the user; the others finish.
- **Rate limit.** Handled by the wake as today. A ticket that used its 3 resumes and stays blocked: `drain rate-limit <PREFIX>-N`.
- **CI red.** While a run is active, the child task gains the line `No Hands run: if CI is still red after 3 fix pushes, stop with BLOCKED:.`, so a CI loop ends as a blocked ticket. Runs outside No Hands are unchanged.
- **Cost cap**, cost unknown, the setting turned off, the start message no longer verifies: `stop`. Running children are cancelled, because money is the limit.
- **Normal end.** The slot fill gets `todo: none` and the Backlog pick says the Backlog is dry, and no ticket of the run is active or queued: `end backlog-empty`. `paused` is not set, since nothing is left to start; tickets waiting on the user stay waiting.
- **`stop everything`** runs the kill switch as today and then `no_hands.py end stopped-by-user`. `resume` never starts a run again: the user sends `no hands` for a new one. `resume` also relays tickets with note `stopped by No Hands: …`, like `stopped by the user`, under the tolerance.
- **`no hands off`**: `drain stopped-by-user`, so tickets in flight finish; `stop everything` is the hard stop.
- **`cancel N`** cancels that one ticket, as today; the run goes on.

A run that has ended stays ended. Nothing but the user's next `no hands` starts another.

### Reporting

- Each auto-approval still posts the full spec or merge block as a notice, ending `Auto-approved under No Hands; the build has started.` (or `merging now.`), and the ticket comment says `auto-approved the <spec|merge> at <time> under No Hands (Risk: …)`.
- Every Chief of Staff report and `status` answer starts with `No Hands on: 3 of 10 tickets, $42 of $200.` (or `No Hands draining: <reason>, …`) while a run is active, so the user can see it is on.
- When a run ends, the Chief of Staff posts a summary: why it ended, how long it ran, tickets started and merged (with costs), tickets waiting on the user and why (hands path, migration, flag, blocked), total cost against the cap, and `Say "resume" to go on without No Hands, or "no hands" for a new run.` when it paused.

## Builds

1. **Setting.** `project_config.no_hands_setting()` returns `(on, ticket_cap, cost_cap, note)` from the three rows on `origin/<target>`, `off` on anything missing or bad. The three rows go into `docs/agents/project.md` (value `off`, `10`, `200`) and `agent-team/templates/project.md` (same), so `set up this repo` seeds them off.
2. **`no_hands.py`** with `start`, `check`, `drain`, `end` and `active()`, as above; `cos_state.py` gets the `noHands` top-level key, its shape check, a `no-hands` op that only `no_hands.py` uses, and the `start` op's append to `started`.
3. **Approval scripts.** `approval_policy.py`: `HANDS_PATH` and `on_hands_path()`; `decide` and `cmd_auto` say auto under an active run for every level and for unrated; `check no-hands`. `cos_approve_pr.py --auto`: under an active run, `auto_gate` skips the tolerance and uses the hands path in place of the approval path, and keeps the rename, file-count, flag, migration and conflict-note stops. Observation tickets stay a Chief of Staff check in `approvals.md`, skipped under an active run.
4. **Slot fill.** `cos_tick.py` prints `run … no_hands.py check` while a run is active and drops `start-todo` lines on `drain` or `stop`, with a `report (filling stopped: No Hands <reason>)` line.
5. **Skill and role text.** A new `chief-of-staff/no-hands.md` (commands, the run table, the end steps, the summary) linked from `SKILL.md` § When to read a reference file and § Commands (`no hands`, `no hands off`); `approvals.md` § Auto-approval (No Hands rule, notice wording, observation tickets, the hands path); `kill-switch.md` (end the run on stop, `resume` relays `stopped by No Hands` and never starts a run); `state-keys.md` (`noHands`); `SKILL.md` § Child task template (the CI line), § Report format (the No Hands line); `project-manager/SKILL.md` § Backlog pick (no pick while draining; a dry Backlog may end the run); `ship-loop` § Approvals (the No Hands notice and `check no-hands`); `docs/agents/chief-of-staff.md` and `org-chart.md` (the user approves nothing during a run except hands-path, migration and flagged changes, and starts and stops runs).
6. **Tests**, one table-driven test per rule:
   - `test_approval_policy.py`: with no run, `decide` is unchanged for every tolerance and level; with an active run, Low, Medium, High and unrated are auto; a run with the setting `off`, a run that ended, a run over its cost cap and a run whose start message is not the user's are not.
   - `test_cos_approve_pr.py`: under an active run, a PR touching `agent-team/scripts/cos_rank.py` is auto, and PRs touching each kind of hands-path file, a renamed file, a migration, a flag path or an unreviewed conflict note are asked. With no run, today's table still passes.
   - `test_no_hands.py`: `start` refuses without the user's message, with the setting off and with a run active; `check` gives `drain ticket-cap` at the cap, `stop cost-cap` at the cost cap and `stop cost unknown` on an unreadable cost.
   - `test_project_config.py`: missing rows, an unknown value and a bad cap read as off.
   - `test_cos_tick.py`: `drain` and `stop` print no `start-todo`.
   - A hands-path import test: every local import of a hands-path script is on the hands path.

## Leaves out

- The three tolerances and how risk is rated.
- Any review, CI check or merge gate: none is skipped or shortened.
- Cross-repo requests (`cross-repo.md`) keep their rules; a run starts only this repo's own Todo and Backlog tickets.
- The status pane and the dashboard; the No Hands line shows in Chief of Staff reports and `status` only.
- The app-side install PR: this repo's `project.md` gets its rows in this PR; each app gets the rows from the template on `set up this repo`, and until then reads as off.

## Calls I made (surprising first)

- ⚠ **Starting a run needs both a committed setting and the user's `no hands` command.** The ticket offered either; with both, a run can't start from a ticket, a PR, a child or a state edit, and the caps have a clear start to count from.
- ⚠ **Under No Hands, merges are held back by a short "hands path", not today's approval path.** Today's path covers all of `scripts/` and every dot-directory, which in this repo is nearly every PR, so the mode would do almost nothing here. The hands path keeps the user on the files that decide approvals, the mode, its caps, the reviews and merge gates, CI, and the always-on instructions. Other script and skill changes merge without the user during a run.
- ⚠ **Migrations and `flag:` paths (money, auth, user email) still wait for the user at merge**, but their specs are auto-approved. So a High-risk spec builds without the user, and its merge waits only when the PR itself hits one of those paths.
- ⚠ **Proposed caps: 10 tickets and $200 API-equivalent per run.** About $15 a ticket from recent merges, with room for a few large ones.
- ⚠ **The cost cap is a hard stop**: running children are cancelled and their tickets blocked, like `stop everything`. An unknown cost also stops the run. The ticket cap and a blocked ticket drain instead: no new starts, and tickets in flight finish under No Hands.
- ⚠ **A run that ends by a cap or a blocked ticket sets `paused`**, so the team sits still until the user reads the summary and says `resume` (which goes on under the tolerance). A run that ends because the Backlog is empty does not pause.
- **One blocked ticket drains the run.** A blocked child usually needs a product answer; one is enough to stop piling on more unattended work.
- **`cancel N` stops that ticket only; the run goes on.** The ticket's "end the run" reads as applying to `stop everything`.
- **`no hands off` drains; `stop everything` is the hard stop.**
- **"CI red after N fixes" is 3 fix pushes, only in No Hands runs**, through a line in the child task, so runs outside the mode are unchanged.
- **A new top-level state key `noHands`.** It is a run record (start, starter message, started tickets, end), not a setting, and the approval scripts re-verify the user's start message from T3's message store before trusting it.
- **Observation tickets are auto-approved during a run**, as the ticket asks, still subject to the hands path.
- **Cost is the sum of `agent_usage.py --ticket` over the run's tickets**, so work on other tickets during the run (a hygiene child, a ticket helper) does not count against it.

## Acceptance

- With no run, behaviour is unchanged under `strict`, `balanced` and `permissive` (the existing approval tests pass unchanged).
- With a run active, a High-risk spec, an unrated ticket and an observation ticket are approved without a user message, and their blocks are still posted as notices.
- Under a run, a PR touching a hands-path file waits for the user and one touching only other scripts does not; both are tested.
- The run drains at the ticket cap and after a blocked ticket, stops at the cost cap, ends when the Backlog is dry, reports why each time, and never starts again by itself.
- `stop everything` ends a run in progress; `resume` does not start one.
- A `noHands` key in state without the user's own `no hands` message, a ticket, a PR or a child cannot start a run or raise a cap.
- `set up this repo` seeds the rows `off`, and a `project.md` with no rows reads as off.
