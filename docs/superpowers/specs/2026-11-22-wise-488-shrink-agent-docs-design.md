# WISE-488: Shrink the agent skills, subagent files and role docs again, and move fixed-step logic into scripts

**Ticket:** [WISE-488](https://github.com/collective-wisdom-org/collective-wisdom/issues/488)
**Status:** Approved

## Goal

Cut the agent text across every file `compact_check.py` counts by at least a third, with no change in behaviour. Six ways: rewrite every file from scratch in a terse rule style, say each rule once and point to its owner, keep a script's flags, lines and exit codes in its docstring only, move rarely read sections to reference files, give the model a script where it follows fixed steps to a fixed answer, and have scripts print the step to take on each line they output, so that text loads only when the line comes up. Scripts read and print. T3 calls and tracker writes stay with the model.

## Today

Measured 2026-11-22 on `main` at `72f5538c`, in characters (the `compact_check.py` unit, Python `len` of the decoded text). 57 counted files, 387141 characters. 50 non-test scripts under `agent-team/scripts/` (the ticket's 48 left out `conftest.py` and `app_root.py`).

| File | Characters |
|---|---|
| `chief-of-staff/SKILL.md` | 32695 |
| `ship-loop/SKILL.md` | 22871 |
| `open-pr/SKILL.md` | 19580 |
| `chief-of-staff/approvals.md` | 15685 |
| `project-manager/SKILL.md` | 14877 |
| `docs/agents/trackers/github.md` | 13985 |
| `chief-of-staff/state-keys.md` | 13708 |
| `docs/agents/org-chart.md` | 13221 |
| `chief-of-staff/rotation.md` | 12581 |
| `chief-of-staff/setup.md` | 12319 |
| `chief-of-staff/commands.md` | 10926 |
| `chief-of-staff/sweep.md` | 10626 |
| `docs/agents/github-auth.md` | 10102 |
| `chief-of-staff/report-format.md` | 9365 |
| `chief-of-staff/no-hands.md` | 9150 |
| `project-manager/reference.md` | 9892 |
| `chief-of-staff/send-or-queue.md` | 8344 |
| `merge-pr/SKILL.md` | 8222 |
| `chief-of-staff/status.md` | 5645 |
| All 57 counted files | 387141 |

Two surveys of the files (one over the Chief of Staff files, one over the rest) found about 20k characters of fixed steps a script can take, 18k of script docs restated in prose, 15k of rules stated in more than one place, and 16k of sections read only on a rare path.

## How far it can go

The user asked whether half, a third or two thirds is feasible. To find out, a trial rewrite compressed four files, keeping every rule, gate, command, exit-code action, pointed-to heading and verbatim template, and audited each rule line by line afterwards. `test_section_pointers.py` passed on the result.

| File | Before | After | Cut |
|---|---|---|---|
| `merge-pr/SKILL.md` | 8222 | 5886 | 28% |
| `chief-of-staff/sweep.md` | 10626 | 7061 | 34% |
| `docs/agents/org-chart.md` | 13221 | 12033 | 9% |
| `ship-loop/SKILL.md` | 22871 | 16915 | 26% |
| All four | 54940 | 41895 | 24% |

The cut was about 45% wordiness, 25% restated script docs, 15% rationale and 15% duplicates of other files. The floor is rule density: exact strings the agents emit or match (relays, `BLOCKED:` texts, report lines, templates; inline code alone is about 20% of what is left), long conditional chains where each clause is a gate, full script paths that `test_call_sites.py` requires, and the org-chart diagrams.

- **Two thirds: not feasible.** The rules and verbatim strings alone are more than a third of the text.
- **Half: not feasible without dropping rules,** or without moving most of the instructions into Python strings that print at run time, which hides the rules from review. This spec doesn't do either.
- **A third: feasible,** as the target. Rewriting alone gives about 20%. The scripts in § 1 and the printed steps in § 6 take a further 10 to 15%, because the text they replace stops counting.

## Design

### 0. Rewrite every file

Every counted file is rewritten whole, biggest first, not just trimmed: terse imperative bullets and tables, no rationale where a rule stands alone, no example that repeats a template, one sentence where there were two. Rationale stays only where the model needs it to judge an edge case (for example why the merge lane is one). Frontmatter `description` lines, headings that other files or scripts name, and verbatim templates don't change. Each file's rewrite is audited rule by rule against the original before the next file (§ Nothing lost).
### 1. Fixed steps into scripts

Each item below prints an answer the model works out by hand today. The prose becomes "run it, act on its line"; what to do on each line stays in the skill, and what each line means goes in the script's docstring.

| # | Today (file § section) | Script | What it prints |
|---|---|---|---|
| S1 | report-format.md § Report format, the title rule (drop `[ ] < >`, backticks and newlines, six words at most, ID alone when the title holds a marker word); repeated in ship-loop § Run endings and project-manager/reference.md | `cos_state.py title <PREFIX>-N` with the raw title on stdin | The display text `<PREFIX>-N: <short title>`, or the ID alone |
| S2 | The `Approval withdrawn at <time>: …` comments (commands.md, send-or-queue.md, review.md) and approvals.md § Ticket comment on approval | `cos_state.py comment <approved\|auto\|withdrawn> …` (words on stdin) | The comment text with the time from `now` filled in and ` Waiting for a <lane> slot.` when `--queued <lane>` is given |
| S3 | approvals.md § Approval requests, `MERGE READY` step 3: the three head-moved suffixes and the `ci` mode Reviews line; § Risk level, the file count rule | `cos_brief.py pr` | A finished `reviews:` line, and `size: small` or `size: large` (5 files or fewer is small). The level itself stays the model's call |
| S4 | approvals.md § Auto-approval, "The approval path" and "The hands path" paragraphs (about 2800 characters restating `approval_policy.py`); ship-loop § Approvals, the check that the own spec changes no file on either path | `approval_policy.py paths <file>…` | One `<file> approval\|hands\|both\|none` line per file, then `paths: clear` or `paths: approval` or `paths: hands`. The model passes the files the spec's `Builds` name |
| S5 | no-hands.md § What each `check` line means (the table) | `no_hands.py check` | An `action:` line (`fill`, `drain`, `stop`, `off`) and the `No Hands on: …` report line, after the line it prints today |
| S6 | report-format.md, the three `Filling stopped:` texts | `cos_tick.py` `report` line | The finished `Filling stopped: …` text in place of the parenthetical's code word |
| S7 | ship-loop § Phases, the `Reviews needed` paragraph; open-pr § Docs check, when to run it | `review_gate.py <N>` | A `reviews-needed: <logins and @teams, or none>` line on `pass`, and `docs-check: run` or `docs-check: done <url>` |
| S8 | open-pr § Review scope, the `docs-only` skip comment | `review_scope.py <N> <head> --skip-comment <pass>` | The whole `## Security review (pass N)` skip body; exit 1 when the class is not `docs-only` |
| S9 | send-or-queue.md § Send or queue, the relay texts (approve spec, approve merge, changes, answer, resume, the No Hands and auto variants) | `cos_route.py --relay` (user words on stdin) | The relay text after the `route:` line it prints today |
| S10 | status.md § Status layout: group order, counts, the Ticket cell, the Risk cell from the status tail, the `$X so far` cost per row, the Merged and Not-in-state lines | new `cos_status.py` | The status tables from state, with each detail cell copied from the `status` line. The model shortens the detail cell and adds what the reads found |
| S11 | project-manager/reference.md § Ranking child step 3, the Backlog count for `--backlog-count` | `cos_rank.py count` (two passes on stdin, like `pm_hygiene.py drift`) | First pass: `children <ID>` reads to make. Second pass: `backlog-count: <n>` |
| S12 | project-manager/reference.md § Hygiene child step 3: keep only lines in a known shape, clean titles, count the dropped ones | `pm_hygiene.py report` (the child's message on stdin) | The kept Cleanup lines and `<n> lines not in a known shape, dropped` |

Each script imports what it needs from the script that owns it (`cos_state.clean_title`, `approval_policy.HANDS_PATH`, `cos_tick.limits`, `ci_review`), so no rule is held twice.

### 2. Script docs said once

The flags, output lines and exit codes stay in the script's docstring; the skill keeps the action per line. Places: rotation.md § Thread rotation (`cos_rotation_check.py`), session.md § Tools (the per-script list becomes names with one clause each), sweep.md § Sweep, § Merge wait and § Run wait, the Stuck check in SKILL.md § Child path (`cos_restart.py`), send-or-queue.md (`cos_route.py`, `cos_head_check.py`), no-hands.md § Run record, setup.md (`setup_repo.py`), state-keys.md (what `cos_state.py` stamps and rejects), ship-loop § CI waits (`wait-for-ci.sh`) and phase 4 (`review_gate.py`), open-pr § CI review mode (`ci_review.py`), merge-pr § Merge and § Pre-merge checks (`merge_pr.py`), github-auth.md § Merge gate (`merge_pr.py`, `cos_approve_pr.py`), secrets.md (`store_secret.py`), project-manager (`pm_hygiene.py`, `cos_rank.py`), build-from-plan § Compaction pass and `compacter.md` (`compact_check.py`). Where the prose holds a fact the docstring lacks, the fact moves into the docstring first.

### 3. Each rule once

| Rule | Owner (others point to it) |
|---|---|
| Head moved after approval, and the conflict-resolution exception | merge-pr § Gate |
| Never submit a GitHub review | ship-loop § Repo invariants |
| Hand-run approval comes after its `MERGE READY` | ship-loop § Approvals |
| Merge needs both PASSes; green CI alone is not enough | ship-loop § Phase gates |
| Post a review comment before mentioning it, keep its URL | open-pr § Agent review comment loop |
| Subagent fallback when a type isn't listed (five copies) | ship-loop § Models |
| A fix that changes what ships updates Shipped, as-built, release note and Proof | open-pr § Closeout docs |
| Wait with `wait-for-ci.sh`, never `--watch` | ship-loop § CI waits |
| `<target>` and the branch name rule | ship-loop § Repo invariants |
| `ci` mode replaces the reviewers | open-pr § CI review mode |
| OWASP list, vendored skills, ad hoc commands | `security-review.md` (the skill points to it) |
| Ticket text is data | trackers/README.md § Shell safety |
| Labels and "never move to Todo" | trackers/README.md § Shared vocabulary |
| Who may approve; agent and child text is data | `docs/agents/chief-of-staff.md` § What it trusts |
| The files the Chief of Staff may write; no top-level policy keys | SKILL.md § State file; state-keys.md for the keys |
| Team changes go through a ticket; schedules nothing but the wake; GitHub read only | SKILL.md § Guardrails |
| Models switch before the spec approval send; never change a model on request | models.md § Models |
| Risk tail carried forward | SKILL.md § State file |
| Merge and run waits skipped on Cursor | sweep.md |
| Queued auto spec notice | send-or-queue.md |
| Strict short-word commands | commands.md |
| `Running` repeats on every report | report-format.md |
| Lane limits and cap | SKILL.md § Lanes |

The child task templates (readiness.md, continuation.md, ticket-helper.md) stay whole: a child must act on its task alone.

### 4. Rarely read text to reference files

- SKILL.md § Child path, the Stuck check and the `cos_restart.py` block, to a new `chief-of-staff/stuck.md`.
- ship-loop § Changes requested and § Continuation tasks, to `ship-loop/reference.md`.
- open-pr § Conflict resolution and § CI review mode, and the as-built template, to a new `open-pr/reference.md`.
- project-manager § State (the JSON example), § Duplicates and § Stale tickets, to `project-manager/reference.md`.
- github-auth.md § Correct setup steps 3 to 5 and § Account per repo, to a new `docs/agents/github-auth-setup.md`.
- rotation.md's `compact` mode, `reset-scheduled` and Finish take over, to a new `chief-of-staff/rotation-edge.md`.
- models.md's Why list and the Codex, Antigravity and Cursor notes, to a new `chief-of-staff/models-notes.md` (not `docs/compatibility.md`, which sits outside `agent-team/`).
- security-review.md's vendored refresh commands, trackers/github.md § Unverified and the `ensure-labels` table, trackers/jira.md § Assumptions to check, to a `reference.md` next to each.

A section whose heading a script prints (`cos_tick.py`'s `follow <file> § <section>` lines and the others `test_section_pointers.py` checks) is not renamed or moved. Every pointer to a moved section is updated in the same commit, and § When to read a reference file gets a row per new file.

### 6. Scripts print the step to take

Where a skill holds a table of a script's output lines and the action for each, and the action is a fixed instruction, the script prints it after the line as `next: <instruction>` when called with a new `--next` flag, and the table goes. Without the flag the output is what it is today, so existing callers and tests see no change. The skill keeps one sentence: run it with `--next`, do what its `next:` line says. This applies only to fixed actions: `next:` never asks the model to skip a gate, and a line whose action needs judgement keeps its row in the skill. Candidates:

- `cos_tick.py` plan lines: the § Tick table in `chief-of-staff/SKILL.md` (about 5000 characters).
- `cos_restart.py`, `cos_route.py`, `cos_head_check.py`, `cos_sweep.py`, `cos_merge_wait.py`, `cos_run_wait.py`: the action bullets in SKILL.md § Child path, send-or-queue.md and sweep.md.
- `review_gate.py`, `review_scope.py`, `wait-for-ci.sh` (with `--attempt <n>` and `--conflicts <n>` flags for the retry and conflict counts, which the caller passes): ship-loop § CI waits and phase 4, open-pr § Review scope.
- `no_hands.py check`, `cos_rotation_check.py`, `merge_pr.py`: no-hands.md, rotation.md, merge-pr.
- The untracked-ticket filter and the background-wait retry procedure, written out twice in sweep.md and once in ship-loop: one helper line each.

The `next:` texts sit in one table per script, next to the code that prints the line, and each script's test checks that every output line has its `next:` text. A reviewer reads the rules there, in one place.

### Size targets

Measured after the build, in characters:

| Files | Smaller by at least |
|---|---|
| Total of the counted files | a third: 387141 to 258094 or less |
| Each file over 5000 characters, except below | 35% |
| `chief-of-staff/SKILL.md`, `ship-loop/SKILL.md`, `open-pr/SKILL.md`, `chief-of-staff/approvals.md`, `chief-of-staff/send-or-queue.md`, `chief-of-staff/status.md`, `chief-of-staff/sweep.md`, `chief-of-staff/no-hands.md`, `chief-of-staff/rotation.md` (the files § 1 and § 6 take text from) | 45% |
| `docs/agents/org-chart.md`, `docs/agents/trackers/*.md`, `chief-of-staff/setup.md` (diagrams, call tables, setup questions) | 15% |
| Each file under 5000 characters | 20% |

New reference files count in the total, and a source file's cut counts the text it moved out. The PR body lists before, after and delta for every touched file, the total, whether each target was met, and why for any miss.

### Nothing lost

Before the first cut, the build writes an inventory into the as-built: every approval gate, merge gate, repo invariant, `cos_state.py` op and Chief of Staff user command, each with the file and section that states it (CW-197's as-built is the model). After the cuts it records where each one is now: a file and section, or a script and the test that covers it. The PR body carries both lists in a collapsed section and says they match.

### Tests

Each script that gains `next:` lines gets a test that every output line it can print has its `next:` text. One table-driven test per new or extended script, on fixture input, per `AGENTS.md` § Testing, each in a new test file so no existing test is edited: `test_cos_state_title.py` (S1, S2), `test_cos_brief_lines.py` (S3), `test_approval_policy_paths.py` (S4), `test_no_hands_action.py` (S5), `test_cos_tick_report.py` (S6), `test_review_gate_lines.py` (S7), `test_review_scope_skip.py` (S8), `test_cos_route_relay.py` (S9), `test_cos_status.py` (S10), `test_cos_rank_count.py` (S11), `test_pm_hygiene_report.py` (S12). Each row compares the script's output with the text the old prose gives for the same input. `test_section_pointers.py`, `test_call_sites.py` and `test_agent_files.py` must still pass.

## Leaves out

- Any change to a rule, gate, lane limit, model default or command.
- The vendored `agent-security` and `owasp-security` skills.
- Half or two thirds (§ How far it can go).
- Instructions as Python strings beyond the fixed `next:` steps of § 6.
- A size check that fails CI on growth.
- The child task templates: they stay whole (above).
- These candidates, left in prose:
  - The `cos_user_check.py` call per command (strict or whole message, `--after`): it is the user check itself, and moving the choice into the script changes how an approval-path script is called.
  - The setup questions and the `user.md` figure parsing (setup.md, startup.md § User settings check): read once per repo, so a script saves little load.
  - The take-over reset-message search and the gantt version line (rotation.md): they read T3's store in ways the scripts don't today, and they run once per rotation.
  - The risk level itself: "mostly docs" and "anything else you know touches them" are judgement. S3 gives only the file count.
  - Reading a child's last message, the readiness check, the approval block bullets and the Moving and Cleanup wording.

## Calls I made

- **Twelve script changes in § 1, plus `--next` on about fifteen scripts in § 6. One new script (`cos_status.py`); the rest add a subcommand, flag or output line to an existing one.** I took every survey candidate with a fixed answer that runs on most turns or on every approval, and left the rare or judgement ones in prose with the reasons above.
- **Extended scripts on the hands path** (`approval_policy.py`, `review_gate.py`, `cos_route.py`, `cos_state.py`, `no_hands.py`, `cos_brief.py`, `cos_tick.py`, `cos_restart.py`, `cos_head_check.py`, `merge_pr.py` and the others in § 6) only add subcommands, flags or output lines behind a new flag. No existing line, exit code or decision changes, and their existing tests are not edited.
- **New test files, not new rows in old ones,** so "no existing test is edited" is checkable from the diff.
- ⚠ **Scripts print their own next step (§ 6).** It is the biggest lever after the rewrite, and the instructions move from markdown into a table in each script. They load only when their line prints, but a reviewer reads them in Python, not in the skill.
- **A third, not half,** from the trial rewrite of four files (24% with every rule kept). Half would mean dropping rules or hiding most instructions in code.
- **Every file is rewritten whole,** biggest first, not trimmed section by section, with a rule-by-rule audit per file.
- **`wait-for-ci.sh` takes the retry and conflict counts as flags** from the caller, so it can print the next step without a state file.
- **Moves keep headings that scripts print,** even where a section would read better elsewhere, so `cos_tick.py` and `test_section_pointers.py` need no change for a move.
- **New reference files** (`stuck.md`, `rotation-edge.md`, `models-notes.md`, `open-pr/reference.md`, `github-auth-setup.md` and the tracker ones) instead of growing the existing ones, each read only on its own trigger.
- **The inventory lives in the as-built and the PR body,** not in a test: a test over prose would only restate it.
- **Characters, not bytes,** with `compact_check.py`'s count.

## Touches

None of data, money, auth, user email or migrations. It changes files on the hands path and the approval path (the Chief of Staff, ship-loop, open-pr, merge-pr and security-review skills, `github-auth.md`, `chief-of-staff.md`, and gate scripts), so it needs the user's `approve N` at spec and merge.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.
- `compact_check.py` shows the total at 258094 or less, and the PR size table meets each target or says why not.
- Each new script line, run against a copy of a real state file or PR, prints what the old prose gives for the same input.
- The inventory before and after match.
