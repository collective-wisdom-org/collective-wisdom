# WISE-488 plan: shrink the agent docs, move fixed steps into scripts

Spec: `docs/superpowers/specs/2026-11-22-wise-488-shrink-agent-docs-design.md` (approved by the user, 2026-11-22).

Test command: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

Rules for every task: no existing test file is edited; new tests go in new files (table-driven, `AGENTS.md` § Testing); a script without its new flag prints exactly what it prints today; never drop or alter a rule, gate, command, exit-code action, verbatim template, frontmatter `description`, or a heading another file or script points to (`test_section_pointers.py`, `test_call_sites.py`, `test_agent_files.py` must pass); full script paths stay (`test_call_sites.py`). Do not commit or push: the parent commits.

## Task 0: baseline and inventory

- Record `compact_check.py`-style sizes of all 57 counted files in `docs/superpowers/as-built/2026-11-22-wise-488-shrink-agent-docs-as-built.md` (`## Sizes before`).
- Write `## Inventory before` in the same file in CW-197's shape (`docs/superpowers/as-built/2026-11-08-cw-197-compact-skills-again-as-built.md`): every approval gate, merge gate, repo invariant, `cos_state.py` op and Chief of Staff user command, with the file and `§ Section` that states it. Searched: all counted files and the script docstrings.

## Task 1: scripts, group A (state and brief)

New subcommands or flags, each with a docstring entry, behind new arguments only: S1 `cos_state.py title`, S2 `cos_state.py comment`, S3 `cos_brief.py pr` `reviews:` and `size:` lines, S4 `approval_policy.py paths`. Tests: `test_cos_state_title.py`, `test_cos_brief_lines.py`, `test_approval_policy_paths.py`.

## Task 2: scripts, group B (review, CI, relay, rank)

S7 `review_gate.py` (`reviews-needed:`, `docs-check:` lines), S8 `review_scope.py --skip-comment`, S9 `cos_route.py --relay`, S11 `cos_rank.py count`, S12 `pm_hygiene.py report`. `wait-for-ci.sh --attempt/--conflicts --next`. Tests: `test_review_gate_lines.py`, `test_review_scope_skip.py`, `test_cos_route_relay.py`, `test_cos_rank_count.py`, `test_pm_hygiene_report.py`.

## Task 3: scripts, group C (tick, status, No Hands, restart)

S5 `no_hands.py check` `action:` line, S6 `cos_tick.py` finished `Filling stopped:` text, S10 new `cos_status.py`. Tests: `test_no_hands_action.py`, `test_cos_tick_report.py`, `test_cos_status.py`.

## Task 4: `--next` flag

`--next` on `cos_tick.py`, `cos_restart.py`, `cos_route.py`, `cos_head_check.py`, `cos_sweep.py`, `cos_merge_wait.py`, `cos_run_wait.py`, `review_gate.py`, `review_scope.py`, `wait-for-ci.sh`, `no_hands.py check`, `cos_rotation_check.py`, `merge_pr.py` (last line only): after each output line whose action is fixed, print `next: <instruction>` taken from one table per script. Never for a line whose action needs judgement. Test per script (`test_next_<script>.py`): every output line the script can print has a `next:` text, and without the flag the output is unchanged.

Tasks 1 to 4 touch disjoint script files except where noted (`cos_route.py`, `review_gate.py`, `review_scope.py`, `no_hands.py`, `cos_tick.py` get both a Task 1 to 3 change and a `--next` change: the same agent does both).

## Tasks 5 to 10: rewrite the docs (after Tasks 1 to 4)

Rewrite whole, in terse rule style, cutting rationale, restated script docs (the docstring owns flags, lines and exit codes), duplicate rules (§ 3 table of the spec, pointing to the owner), and moving rarely read sections to the reference files named in spec § 4. Replace action tables of scripts that now print `next:` with "run it with `--next`, do what it says". Audit each file rule by rule against the original before moving on. Groups, disjoint:

- Task 5: `chief-of-staff/SKILL.md`, `stuck.md` (new), `rotation.md`, `rotation-edge.md` (new), `startup.md`, `session.md`, `rate-limit.md`, `fallbacks.md`, `kill-switch.md`.
- Task 6: `chief-of-staff/approvals.md`, `send-or-queue.md`, `commands.md`, `review.md`, `continuation.md`, `adopt.md`.
- Task 7: `chief-of-staff/sweep.md`, `report-format.md`, `status.md`, `no-hands.md`, `state-keys.md`, `readiness.md`, `models.md`, `models-notes.md` (new), `cross-repo.md`, `ticket-helper.md`, `setup.md`.
- Task 8: `ship-loop/SKILL.md`, `ship-loop/reference.md`, `open-pr/SKILL.md`, `open-pr/reference.md` (new), `merge-pr/SKILL.md`, `security-review/SKILL.md`, `build-from-plan`, `kickoff-feature`, `write-ticket`.
- Task 9: `project-manager/SKILL.md`, `project-manager/reference.md`, `human-writing/*`, `auditing-security`.
- Task 10: `docs/agents/**` (`org-chart.md`, `chief-of-staff.md`, `github-auth.md`, `github-auth-setup.md` new, `security-review.md`, `code-review.md`, `documenter.md`, `secrets.md`, `compacter.md`, `README.md`, `trackers/*`), `.claude/agents/*.md` and `.cursor/agents/*.md` (edit together), `templates/AGENTS.md`.

Update every `§` pointer to a moved section in the same task. Each new reference file gets a row in the owning skill's "When to read a reference file" or equivalent.

## Task 11: close the inventory and measure

- Write `## Inventory after` and `## Sizes after` in the as-built; run `compact_check.py`; check the targets in spec § Size targets; list misses with reasons.
- Run the test command and shellcheck.
