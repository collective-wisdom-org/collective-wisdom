# CW-23: Shrink the files agents load without changing behaviour

Ticket: https://github.com/dbeallor/collective-wisdom/issues/23

## Intent

Every agent loads the agent-team skills and role docs, and the Chief of Staff loads the largest one in a long-lived thread. Make them smaller without changing what the team does: no rule, gate, lane limit, model default or command changes.

## What is here today

Measured on `origin/main` at `e835684`, 2026-11-03. Characters, about 4 per token.

| File | Lines | Characters | Ticket's measure |
|---|---|---|---|
| `.claude/skills/chief-of-staff/SKILL.md` | 889 | 101297 | 78024 |
| `.claude/skills/project-manager/SKILL.md` | 234 | 20445 | 20445 |
| `.claude/skills/agent-security/SKILL.md` (vendored) | 349 | 19604 | 19604 |
| `.claude/skills/ship-loop/SKILL.md` | 162 | 17054 | 16219 |
| `.claude/skills/owasp-security/SKILL.md` (vendored) | 206 | 14059 | 14059 |
| `docs/agents/trackers/github.md` | 193 | 12572 | 12572 |
| `.claude/skills/open-pr/SKILL.md` | 164 | 10942 | 10411 |
| `docs/agents/org-chart.md` | 125 | 10556 | 9986 |
| `.claude/skills/chief-of-staff/reference.md` | 58 | 8623 | 8264 |
| `.claude/skills/merge-pr/SKILL.md` | 72 | 8589 | 8501 |

The Chief of Staff skill grew 30% since the ticket was written (CW-14, CW-16, CW-17, CW-21 merged). It is now 36% of the 285079 characters in the ticket's groups. Its largest sections:

| Section | Characters | Used |
|---|---|---|
| Send or queue | 10151 | every relay |
| Thread rotation | 9778 | rotation, take over, resume; the Moved-to check runs every turn |
| Commands | 7890 | every user message |
| Full pass | 7464 | every user message |
| Lean turns | 7254 | every child notice |
| State file | 6776 | every turn (commands), schema detail rarely |
| Cross-repo requests | 6526 | only on a request to or from another repo |
| Slot fill | 4628 | every child notice |
| Approval requests | 4216 | every SPEC READY and MERGE READY |
| Report format (with Status layout) | 7787 | every report |
| Ticket helper | 3414 | only on a ticket request |

`reference.md` already holds Setup, State rebuild, Kill switch and three Thread rotation modes, and the skill points to them by section name.

Duplication found in a first pass (the builder makes the full list):

- The `./scripts/gh.sh`, never bare `gh` rule is restated in `project-manager`, `open-pr`, `chief-of-staff`, `ship-loop`, `trackers/github.md`, `templates/project.md` and `templates/AGENTS.md`.
- "Tracker operations are in `docs/agents/trackers/README.md`; the adapter is the one for the `Tracker` row" is restated in `kickoff-feature`, `write-ticket`, `project-manager`, `open-pr`, `merge-pr` and `ship-loop`.
- `ship-loop` § Repo invariants says "do not copy this block elsewhere", but `kickoff-feature` § Tracker & branch and others restate the branch pattern and the one ticket, one branch, one PR rule.
- Shell quoting rules appear in `chief-of-staff`, `trackers/README.md` and `trackers/github.md`.

Scripts that read these files: `cos_rotation_check.py` hashes `.claude/skills/chief-of-staff/`, `.claude/skills/project-manager/` and `docs/agents/chief-of-staff.md` for `skillCommit` (whole directories, so new reference files inside them are covered). `test_tracker_docs.py` needs a `### \`op\`` heading in each adapter for every operation in `trackers/README.md`. No script parses skill prose.

## Overlap with open work, and what must merge first

Every large file is being edited by open work. Building now would conflict and could undo their rules.

| Work | State | Files it shares with CW-23 |
|---|---|---|
| PR #47 (CW-42, install update) | open | `ship-loop`, `merge-pr` SKILL.md, root `AGENTS.md` |
| PR #48 (CW-38, role GitHub users) | open | `chief-of-staff`, `project-manager`, `ship-loop`, `open-pr`, `merge-pr`, `security-review`, `write-ticket` SKILL.md; `docs/agents/README.md`, `github-auth.md`, `org-chart.md`, `trackers/github.md`; adds `personas.md` |
| CW-20 (hand change requests to collective-wisdom) | spec only | `chief-of-staff` SKILL.md (Commands, Cross-repo requests, Guardrails, Tools) and maybe `reference.md`; `docs/agents/chief-of-staff.md`, `org-chart.md` |
| CW-49 (child link in status) | spec only | `chief-of-staff` SKILL.md § Report format "Status layout"; `docs/agents/chief-of-staff.md` |

**The build starts after #47, #48, CW-20 and CW-49 have all merged.** The tickets the ticket lists (#11 to #21) are closed. One PR, cut from `main` at that point, re-measured there.

Per-file order, if the user wants to start earlier: a file is free when none of the four above touches it. Free today: `kickoff-feature` and `build-from-plan` SKILL.md; `trackers/README.md`, `linear.md`, `jira.md`; `docs/agents/security-review.md`, `documenter.md`, `code-review.md`, `implementer.md`, `ticket-writer.md`; `templates/AGENTS.md`. Together they are 34945 of 285079 characters (12%), so an early PR buys little. The rest unlock as follows: `ship-loop`, `merge-pr` after #47 and #48; `project-manager`, `open-pr`, `security-review`, `write-ticket`, `trackers/github.md`, `github-auth.md`, `README.md` after #48; `chief-of-staff` SKILL.md and `reference.md`, `docs/agents/chief-of-staff.md`, `org-chart.md` after #48, CW-20 and CW-49.

## Design

Four kinds of edit, in this order per file.

### 1. Say each shared rule once

Each rule gets one owner, and other files point to it by section (`ship-loop § Repo invariants`):

| Rule | Owner |
|---|---|
| Repo invariants, branch pattern, one ticket one branch one PR, `./scripts/gh.sh` only | `ship-loop` § Repo invariants (which points to `project.md` for the values) |
| Where tracker operations live and which adapter applies | `docs/agents/trackers/README.md` |
| Shell quoting for tracker calls | `docs/agents/trackers/README.md` |
| Team-mode gates (spec, merge, relay check) | `ship-loop` § Team mode |

A pointer replaces a restatement only where the reader already loads the owner. Every skill reads `ship-loop` § Repo invariants first, so a skill can drop its copy. `templates/AGENTS.md` and `templates/project.md` are read by agents outside the skills (Cursor, plain Claude Code sessions), so they keep the `gh.sh` rule.

### 2. Move rarely used sections into reference files

The Chief of Staff keeps its per-turn path in `SKILL.md`: the intro and retired check, Working set, Models, Lanes, State file (commands and keys it reads every turn), Full pass, Send or queue, Slot fill, Lean turns, Merged check, Sweep, Readiness check and start with the child task template, Approval requests with Risk level, Commands, Report format, Guardrails, and from Thread rotation the trigger and the Moved-to check.

Into `chief-of-staff/reference.md`, each under its own heading, with a one-line pointer left in `SKILL.md` saying when to read it:

- Start-up clean-up (runs only at start-up, take over and resume).
- Thread rotation: the handoff and take-over steps, Archiving, and the modes already there.
- Cross-repo requests (only on a request to or from another repo).
- Ticket helper (only when the user asks for a ticket or a team change).
- State file: the schema detail and per-key history that the `cos_state.py` output already shows. The commands and the rules for what may be written stay.

`project-manager`: the Ranking child brief (3773, used only when a ranking child starts) and Stale tickets move to `project-manager/reference.md`. Pass order, Todo fill and Guardrails stay.

`ship-loop`: § Team mode (10653 of 17054) is loaded by every solo run that never uses it. The Relays chain walk (the rotation hop check, about 2000 characters) moves to `ship-loop/reference.md` § Relay chain walk; a child reads it only when the relay has an `Approval in thread:` line naming another thread. The rest of Team mode stays, because every team child needs it.

`trackers/github.md`: Setup and Unverified move to a short `trackers/github-setup.md` only if it saves more than 500 characters after tightening; otherwise they stay. The `### \`op\`` headings stay in the adapter (`test_tracker_docs.py`).

`org-chart.md`: tighten only; it has no rarely used part.

### 3. Tighten what stays

Shorter sentences, no repeated explanations, examples cut to one where two show the same thing. No rule is dropped, softened or reworded into a different rule. Literal strings agents send or match (reply templates, markers like `SPEC READY`, `Moved to`, `CHIEF OF STAFF:`, command names, script arguments) are kept byte for byte.

### 4. Keep every pointer working

A heading another file names (`§ Thread rotation "Failed handoff"`, `§ Lean turns`) keeps its exact text, or every pointer to it changes in the same PR. A new test checks this (below).

### Vendored security skills

`agent-security` and `owasp-security` are left unchanged. `owasp-security` already has a `reference/` split; `agent-security` has no clean split point that would survive a re-sync from upstream. The PR says so.

## Targets

- Chief of Staff `SKILL.md`: at least 35% smaller than its size at the start of the build. On today's 101297 that is 65800 or less. The moved sections alone are about 21000; tightening and dedup cover the rest.
- Everything in the ticket's size table, together: at least 20% smaller than at the start of the build, counting new reference files.
- `reference.md` files grow; that is expected and is reported.

## Proving nothing changed

1. **Inventory, before and after.** Before any edit, the builder writes `docs/superpowers/plans/2026-11-03-cw-23-inventory.md`: one row per approval gate, merge gate, repo invariant, `cos_state.py` command and Chief of Staff user command, with the file and section that holds it and the exact rule text. After the edits, a second table with the same rows and their new locations. The diff between the two may differ only in location. A row that can't be matched is a bug in the edit, not in the list. The PR links the file.
2. **Section pointer test.** New `agent-team/scripts/test_section_pointers.py`: one table-driven test that finds every `<file> § <heading>` and `§ <heading>` pointer in the skills, `docs/agents/` and the templates, and checks the named heading exists in the named file (in the same file when no file is named; the skill's `SKILL.md` for `<skill> § X`). A quoted subpart (`"Failed handoff"`) is checked as text in that section, not as a heading. It runs against today's files first; pointers already broken on `main` are listed in the PR and fixed.
3. **Test suite.** `python3 -I -m pytest -q agent-team/scripts` passes. No existing test is edited to pass.
4. **Sizes.** The PR has a before and after table for every file it touches, plus the total.
5. **Review.** Code review compares the inventory rows against the diff, section by section, for rules that changed meaning.

## Rollout

One collective-wisdom PR. Then an install PR in each app (`install.sh`). Merging it changes `skillCommit` for the Chief of Staff's files, so the running Chief of Staff rotates at its next check, as it does for any skill change. Apps have no files only they own that this changes.

## Non-goals

- Any change to a rule, gate, lane limit, model default, command or reply template.
- Behaviour from CW-20, CW-38, CW-42 or CW-49.
- `human-writing` and the vendored security skills' content.
- A size budget enforced by a script or CI check.

## Calls I made (surprising first)

- ⚠ The build waits for PRs #47 and #48 and the CW-20 and CW-49 work to merge, then ships as one PR. An early PR on the free files would cover 12% of the size.
- ⚠ The Chief of Staff target is "35% smaller than at build start", not a fixed number, because the skill has grown from 78024 to 101297 since the ticket and CW-20 and CW-49 will grow it again.
- ⚠ Adds one test, `test_section_pointers.py`, so moved sections can't leave dangling pointers later. The ticket asks only that pointers resolve at merge.
- Cross-repo requests and Ticket helper move out of the Chief of Staff `SKILL.md`. Both run only on a specific request, and the Commands row that triggers them stays.
- `ship-loop` gets a `reference.md` for the relay chain walk. Every solo run loads `ship-loop`, and the chain walk applies only to relays from a rotated Chief of Staff.
- The vendored security skills are untouched.
- `templates/AGENTS.md` and `templates/project.md` keep their `gh.sh` rule even though `ship-loop` owns it, because agents outside the skills read them.
- The inventory lives in `docs/superpowers/plans/` beside the plan, not only in the PR body, so a later ticket can diff against it.

## Left to the builder

- The full duplication list, from a read of every file in scope.
- Which State file and Send or queue detail is schema history versus per-turn rule. When unsure, it stays in `SKILL.md`.
