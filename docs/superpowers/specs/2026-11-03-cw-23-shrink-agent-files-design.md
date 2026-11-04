# CW-23: Shrink the files agents load without changing behaviour

Ticket: https://github.com/dbeallor/collective-wisdom/issues/23 (priority High since the 2026-11-04 note)

## Intent

Every agent loads the agent-team skills and role docs, and the Chief of Staff loads the largest one in a long-lived thread. The live Chief of Staff thread sat at 119k context right after a take-over. Make the files smaller without changing what the team does: no rule, gate, lane limit, model default or command changes here.

The Chief of Staff `SKILL.md` goes under 30000 characters. Rotation, cross-repo requests, the kill switch and the ticket helper move to reference files it reads only when it needs them.

## What is here today

Measured on `origin/main` at `e835684`, 2026-11-03. Characters, about 4 per token.

| File | Lines | Characters |
|---|---|---|
| `.claude/skills/chief-of-staff/SKILL.md` | 889 | 101297 |
| `.claude/skills/project-manager/SKILL.md` | 234 | 20445 |
| `.claude/skills/agent-security/SKILL.md` (vendored) | 349 | 19604 |
| `.claude/skills/ship-loop/SKILL.md` | 162 | 17054 |
| `.claude/skills/owasp-security/SKILL.md` (vendored) | 206 | 14059 |
| `docs/agents/trackers/github.md` | 193 | 12572 |
| `.claude/skills/open-pr/SKILL.md` | 164 | 10942 |
| `docs/agents/org-chart.md` | 125 | 10556 |
| `.claude/skills/chief-of-staff/reference.md` | 58 | 8623 |
| `.claude/skills/merge-pr/SKILL.md` | 72 | 8589 |
| All files in the ticket's groups | | 285079 |

The Chief of Staff skill is 36% of the total. Its sections, in characters:

| Section | Characters | When it is used |
|---|---|---|
| Intro, Tools | ~6000 | every turn |
| Working set | 1081 | every turn |
| Setup (pointer) | 180 | start-up |
| Start-up clean-up | 1352 | start-up, take over, resume |
| Models | 2395 | each spec approval |
| Lanes | 1592 | every turn |
| State file | 6776 | every turn for the commands; key-by-key detail rarely |
| Full pass | 7464 | each user message (#60 replaces it) |
| Send or queue | 10151 | each relay; the continuation-child part only on restarts, answers, resumes |
| Slot fill | 4628 | each child notice (#60 replaces it) |
| Lean turns | 7254 | each child notice (#60 replaces it) |
| Merged check | 2096 | inside the sweep |
| Sweep | 2860 | each child notice |
| Thread rotation | 9778 | rotation, take over, resume |
| Readiness check and start, Child task template | 2253 | each child start |
| Ticket helper | 3414 | only on a ticket request |
| Cross-repo requests | 6526 | only on a request to or from another repo |
| Approval requests, Risk level | 6337 | each `SPEC READY` and `MERGE READY` |
| Commands | 7890 | each user message |
| Kill switch (pointer) | 77 | `stop everything` |
| Report format, Status layout | 7787 | each report; Status layout only on `status` |
| Guardrails | 2279 | every turn |

`reference.md` already holds Setup, State rebuild, Kill switch and three Thread rotation modes.

Duplication found in a first pass (the builder makes the full list):

- The `./scripts/gh.sh`, never bare `gh` rule is restated in `project-manager`, `open-pr`, `chief-of-staff`, `ship-loop`, `trackers/github.md`, `templates/project.md` and `templates/AGENTS.md`.
- "Tracker operations are in `docs/agents/trackers/README.md`; the adapter is the one for the `Tracker` row" is restated in `kickoff-feature`, `write-ticket`, `project-manager`, `open-pr`, `merge-pr` and `ship-loop`.
- `ship-loop` § Repo invariants says "do not copy this block elsewhere", but `kickoff-feature` and others restate the branch pattern and the one ticket, one branch, one PR rule.
- Shell quoting rules appear in `chief-of-staff`, `trackers/README.md` and `trackers/github.md`.

Scripts that read these files: `cos_rotation_check.py` hashes `.claude/skills/chief-of-staff/`, `.claude/skills/project-manager/` and `docs/agents/chief-of-staff.md` for `skillCommit`. It hashes whole directories, so new reference files inside them are covered. `test_tracker_docs.py` needs a `### \`op\`` heading in each adapter for every operation in `trackers/README.md`. No script parses skill prose.

## Order against other work

### Rule changes that go first: #51 and #60

Both remove Chief of Staff rules. CW-23 changes no rule, so it can't make those cuts itself. If they landed after CW-23, they would edit the moved text and the gain would come late. The 2026-11-04 note says to do them with or before this ticket. **This spec puts them before**: one ticket is one PR, and keeping rule changes out of CW-23 is what lets its inventory check (below) prove nothing changed.

- **#51 (trust the state file)** removes the intro's double retirement check, the `parentThreadId` backfill and archive re-read, the wake-task listing before delete, and the worktree re-read in the continuation-child path. It also removes the scripts behind them. That takes several thousand characters out of the intro, State file, Start-up clean-up, Send or queue and Thread rotation.
- **#60 (`cos_tick.py`)** turns § Full pass, § Slot fill and § Lean turns (19346 characters together) into "run `cos_tick.py` and follow its plan", keeping prose only where the model judges.

Without both, the 30000 target can't be met without cutting rules (see Budget).

### #53 (rotate less often)

Not a prerequisite. It edits § Thread rotation's trigger table and `cos_rotation_check.py`. If #53 merges first, CW-23 moves its new text. If CW-23 merges first, #53 edits `rotation.md` instead of `SKILL.md`; the builder of #53 needs only the new path. #53 also records context after take-over in the report line, which gives CW-23 a before and after number, so merging #53 first is better but not required.

### Earlier overlaps

| Work | State | Files it shares with CW-23 |
|---|---|---|
| PR #47 (CW-42, install update) | open | `ship-loop`, `merge-pr` SKILL.md, root `AGENTS.md` |
| PR #48 (CW-38, role GitHub users) | open | `chief-of-staff`, `project-manager`, `ship-loop`, `open-pr`, `merge-pr`, `security-review`, `write-ticket` SKILL.md; `docs/agents/README.md`, `github-auth.md`, `org-chart.md`, `trackers/github.md` |
| PR #61 (CW-49, child link in status) | open | `chief-of-staff` SKILL.md § Report format "Status layout"; `docs/agents/chief-of-staff.md` |
| CW-20 (hand change requests to collective-wisdom) | spec only | `chief-of-staff` SKILL.md § Commands, § Cross-repo requests, § Guardrails, § Tools; `docs/agents/chief-of-staff.md`, `org-chart.md` |
| #51, #60 | not started | `chief-of-staff` SKILL.md and `reference.md`, `docs/agents/chief-of-staff.md`, `cos_*` scripts |

PR #50 (CW-40) touches only a test and its own docs. No overlap.

### What must merge first

**The build starts after #47, #48, #61, CW-20, #51 and #60 have merged.** #53 may land on either side. One PR, cut from `main` at that point and measured again there.

If the user wants to start earlier, files unlock as follows. A file is free when nothing above touches it.

| Files | Free after |
|---|---|
| `kickoff-feature`, `build-from-plan` SKILL.md; `trackers/README.md`, `linear.md`, `jira.md`; `docs/agents/security-review.md`, `documenter.md`, `code-review.md`, `implementer.md`, `ticket-writer.md`; `templates/AGENTS.md` | now (34945 characters, 12% of the total) |
| `ship-loop`, `merge-pr` SKILL.md | #47, #48 |
| `project-manager`, `open-pr`, `security-review`, `write-ticket` SKILL.md; `trackers/github.md`, `github-auth.md`, `docs/agents/README.md` | #48 |
| `org-chart.md` | #48, CW-20 |
| `chief-of-staff` SKILL.md and reference files, `docs/agents/chief-of-staff.md` | #48, #61, CW-20, #51, #60 |

An early PR on the free files saves little. The Chief of Staff skill, which is the point of the ticket, unlocks last.

## Design

Four kinds of edit, in this order per file.

### 1. Say each shared rule once

Each rule gets one owner. Other files point to it by section (`ship-loop § Repo invariants`):

| Rule | Owner |
|---|---|
| Repo invariants, branch pattern, one ticket one branch one PR, `./scripts/gh.sh` only | `ship-loop` § Repo invariants (which points to `project.md` for the values) |
| Where tracker operations live and which adapter applies | `docs/agents/trackers/README.md` |
| Shell quoting for tracker calls | `docs/agents/trackers/README.md` |
| Team-mode gates (spec, merge, relay check) | `ship-loop` § Team mode |
| The Chief of Staff trust boundary (#51 writes it) | `docs/agents/chief-of-staff.md` |

A pointer replaces a restatement only where the reader already loads the owner. Every skill reads `ship-loop` § Repo invariants first, so a skill can drop its copy. `templates/AGENTS.md` and `templates/project.md` are read by agents outside the skills (Cursor, plain Claude Code sessions), so they keep the `gh.sh` rule.

### 2. Chief of Staff: a per-turn core plus reference files

`SKILL.md` keeps what most turns need. Every other part moves to a reference file in `chief-of-staff/`. `SKILL.md` gets one table, § When to read a reference file, near the top: one row per file, with the trigger that makes the Chief of Staff read it. Each pointer elsewhere in `SKILL.md` names the file and section (`rotation.md § Take over`).

`SKILL.md` keeps:

- The intro (what wakes the thread, what each wake runs) and Tools.
- Working set, Lanes, Models (the switch runs on each spec approval).
- State file: the `cos_state.py` commands and which keys a turn reads or writes.
- The `cos_tick.py` turn plan from #60, with the prose #60 keeps for judgment.
- Send or queue: the core send path, queueing and the head check.
- Sweep and Merged check, in the short form the sweep script allows.
- Readiness check and start, with the child task template.
- Commands: the table, each row one line, pointing to the reference file for long handling.
- Report format: the report shape and rules for the routine report.
- Guardrails.

The reference files:

| File | Holds | Read when |
|---|---|---|
| `startup.md` | Setup, Start-up clean-up, State rebuild, Resume mode, the legacy heartbeat prompt (today's `reference.md` § Setup and § State rebuild, `SKILL.md` § Setup and § Start-up clean-up) | `start the team`, `resume`, the heartbeat prompt, or `cos_state.py show` exits 2 |
| `rotation.md` | Thread rotation whole: the trigger table, the rotation check, handoff, Take over, Archiving, the Moved-to check, Resume mode's take-over steps, Retired thread, Failed handoff (today's `SKILL.md` § Thread rotation and the three `reference.md` rotation sections) | the rotation check says rotate, `take over`, the state says this thread is retired, or a `rotation` is in state |
| `cross-repo.md` | Cross-repo requests: Sending, Receiving, Replies, failure lines, and CW-20's team-change part | the user asks for work in another repo or a change to how the team works (in an app), or a `CHIEF OF STAFF REQUEST` or `REPLY` arrives |
| `ticket-helper.md` | Ticket helper: when it starts, its task text, the helper test for threads not in `tickets` | a new ticket, a ticket edit, "place / link these tickets", or a team change in collective-wisdom |
| `kill-switch.md` | Kill switch, and what `resume` restores (today's `reference.md` § Kill switch and the `resume` row's detail) | `stop everything` or `resume` |
| `approvals.md` | Approval requests, Risk level, the brief inputs from `cos_brief.py`, and the ticket comment on approval | a child ends with `SPEC READY` or `MERGE READY`, or an approval is re-requested |
| `continuation.md` | Send or queue "Continuation child": restarts, answers, resumes and rate-limit continues, the handoff block | a send needs a continuation child (a dead or finished child, a rate-limit continue) |
| `status.md` | Report format "Status layout" (with #61's link rule) and the `where's <PREFIX>-N?` answer | `status` or `where's <PREFIX>-N?` |
| `state-keys.md` | State file key by key: each key's meaning and history, `pendingRelay` shapes, `retiredThreads` entries, unknown keys and `prune` | a state edit the core section doesn't cover, or an `unknown keys:` line |

`reference.md` is removed. Every section in it moves to one of the files above, and every pointer to it changes in the same PR.

### 3. Other skills

- `project-manager`: the Ranking child brief (3773 characters, used only when a ranking child starts) and Stale tickets move to `project-manager/reference.md`. Pass order, Todo fill and Guardrails stay.
- `ship-loop`: the Relays chain walk (the rotation hop check, about 2000 characters) moves to `ship-loop/reference.md` § Relay chain walk. A child reads it only when a relay's `Approval in thread:` line names a thread other than the one in its task. The rest of § Team mode stays, because every team child needs it. (If #51 drops the Moved-to check, the chain walk changes in #51, not here.)
- `trackers/github.md`: tighten only. The `### \`op\`` headings stay (`test_tracker_docs.py`).
- `open-pr`, `merge-pr`, `org-chart.md` and the rest: dedup and tighten only.
- Vendored `agent-security` and `owasp-security`: left unchanged. `owasp-security` already has a `reference/` split. `agent-security` has no clean split point that would survive copying in a newer upstream version. The PR says so.

### 4. Tighten what stays, keep every pointer working

Shorter sentences, no repeated explanations, one example where two show the same thing. No rule is dropped, softened or reworded into a different rule. Literal strings agents send or match (reply templates, markers like `SPEC READY`, `Moved to`, `CHIEF OF STAFF:`, command names, script arguments) stay byte for byte.

A heading another file names keeps its exact text, or every pointer to it changes in the same PR. A new test checks this (below).

## Budget

Target: Chief of Staff `SKILL.md` under 30000 characters, measured with `wc -c`.

Rough budget for what stays, after #51 and #60 have merged:

| Part | Characters |
|---|---|
| Intro and Tools | 3500 |
| When to read a reference file | 1200 |
| Working set, Lanes, Models | 4000 |
| State file core | 2000 |
| Turn plan (`cos_tick.py`) | 2500 |
| Send or queue core | 4500 |
| Sweep, Merged check | 2000 |
| Readiness check and start, child task template | 2300 |
| Commands | 4400 |
| Report format core | 2000 |
| Guardrails | 1500 |
| Total | 29900 |

Without #60, Full pass, Slot fill and Lean turns alone need about 15000 characters even after tightening, and the target can't be met. If the measured size at the end of the build is still over 30000 without cutting a rule, the builder does not cut rules. It stops with `BLOCKED: Chief of Staff SKILL.md is <N> characters after the split; reaching 30000 needs <section> to move or a rule change`, so the user picks.

Other targets:

- Everything in the ticket's size table, together, counting the new reference files: at least 15% smaller than at build start (moving text saves the Chief of Staff, not the total; the total falls through dedup and tightening).
- Reference files grow. The PR reports them.

## Proving nothing changed

1. **Inventory, before and after.** Before any edit, the builder writes `docs/superpowers/plans/<date>-cw-23-inventory.md`: one row per approval gate, merge gate, repo invariant, `cos_state.py` command and Chief of Staff user command, with the file and section that holds it and the exact rule text. After the edits, a second table with the same rows and their new locations. The two may differ only in location. A row that can't be matched is a bug in the edit, not in the list. The PR links the file.
2. **Section pointer test.** New `agent-team/scripts/test_section_pointers.py`: one table-driven test that finds every `<file> § <heading>` and `§ <heading>` pointer in the skills, their reference files, `docs/agents/` and the templates, and checks the named heading exists in the named file (the same file when none is named; the skill's `SKILL.md` for `<skill> § X`). A quoted subpart (`"Failed handoff"`) is checked as text in that section, not as a heading. It runs against `main` first; pointers already broken there are listed in the PR and fixed.
3. **Test suite.** `python3 -I -m pytest -q agent-team/scripts` passes. No existing test is edited to pass.
4. **Sizes.** The PR has a before and after table for every file it touches, plus the total and the Chief of Staff's.
5. **Review.** Code review compares the inventory rows against the diff, section by section, for rules that changed meaning.

## Rollout

One collective-wisdom PR, then an install PR in each app (`install.sh` copies the new reference files with the rest of `.claude/skills/`). Merging changes `skillCommit`, so the running Chief of Staff rotates by the rules in force then (#53's, if merged). The new thread loads the smaller skill. Apps have no files of their own that this changes.

## Non-goals

- Any change to a rule, gate, lane limit, model default, command or reply template. #51, #53 and #60 make the rule changes.
- Behaviour from CW-20, CW-38, CW-42 or CW-49.
- `human-writing` and the vendored security skills' content.
- A size limit enforced by a script or CI check.

## Calls I made (surprising first)

- ⚠ #51 and #60 merge **before** CW-23, not in the same PR. CW-23 changes no rule, and that is what lets the inventory prove nothing changed. Without #60 the 30000 target can't be met.
- ⚠ If the Chief of Staff skill is still over 30000 characters after the split, the build stops with `BLOCKED:` and the number, rather than cutting a rule to fit.
- ⚠ `reference.md` is replaced by nine topic files (`startup.md`, `rotation.md`, `cross-repo.md`, `ticket-helper.md`, `kill-switch.md`, `approvals.md`, `continuation.md`, `status.md`, `state-keys.md`), so each trigger loads only what it needs. A single bigger `reference.md` would load the rotation detail on every `status`.
- ⚠ Approval requests and Status layout also move out, beyond the four the note names. Without them the budget doesn't fit; each is read only on its own trigger.
- #53 is not a prerequisite. If CW-23 merges first, #53 edits `rotation.md`.
- Adds one test, `test_section_pointers.py`, so moved sections can't leave pointers to missing headings later. The ticket asks only that pointers work at merge time.
- `ship-loop` gets a reference file for the relay chain walk, because every solo run loads `ship-loop`.
- The vendored security skills are untouched.
- `templates/AGENTS.md` and `templates/project.md` keep their `gh.sh` rule, because agents that don't load the skills read them.
- The total target is 15% smaller, not the Chief of Staff's 70%, because moved text still counts in the total.
- The inventory lives in `docs/superpowers/plans/` beside the plan, not only in the PR body, so a later ticket can diff against it.

## Left to the builder

- The full duplication list, from a read of every file in scope.
- Exact section boundaries after #51 and #60 change the text. When unsure whether a part is per-turn, it stays in `SKILL.md` and counts against the budget.
