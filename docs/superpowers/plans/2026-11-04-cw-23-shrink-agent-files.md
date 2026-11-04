# CW-23 plan: shrink the files agents load

Spec: `docs/superpowers/specs/2026-11-03-cw-23-shrink-agent-files-design.md`. Ticket: https://github.com/dbeallor/collective-wisdom/issues/23.

Built from `main` at `4be5d07`, with `#51` and `#60` **not** merged (the user said `resume 23` anyway). So § Full pass, § Slot fill and § Lean turns stay in the Chief of Staff `SKILL.md`, and the 30000 target is expected to be missed. The spec's stop rule applies: no rule is cut, and the run ends with `BLOCKED:` and the measured size.

Baseline: `uvx pytest -q agent-team/scripts` passes (491). Original files are the ones on `origin/main` (`git show origin/main:<path>`).

## Tasks

Each edit task is for the `implementer` subagent (model `sonnet`). Edit under `agent-team/`, never through the root links.

1. **Inventory before** (read only, then write one file). Write `docs/superpowers/plans/2026-11-04-cw-23-inventory.md` with table 1 "Before": one row per approval gate, merge gate, repo invariant, `cos_state.py` command and Chief of Staff user command. Columns: id, rule (exact text), file, section. Source: `origin/main`.
2. **Pointer test.** New `agent-team/scripts/test_section_pointers.py` (spec § Proving nothing changed, item 2). One table-driven test. Run it on the untouched tree first and list pointers already broken on `main`.
3. **Chief of Staff split.** In `agent-team/.claude/skills/chief-of-staff/` and `agent-team/docs/agents/chief-of-staff.md` only: `SKILL.md` keeps the per-turn core and gets § When to read a reference file; the other parts move, text unchanged except tightening, to `startup.md`, `rotation.md`, `cross-repo.md`, `ticket-helper.md`, `kill-switch.md`, `approvals.md`, `continuation.md`, `status.md`, `state-keys.md`; `reference.md` is removed and every pointer to it changes. Literal strings stay byte for byte.
4. **Other files.** Everything else in the ticket's groups: `project-manager` (Ranking child brief and Stale tickets to `reference.md`), `ship-loop` (Relay chain walk to `reference.md`), dedup of the `gh.sh`, tracker-operations, repo-invariants and shell-quoting restatements, tighten `open-pr`, `merge-pr`, `org-chart.md`, `trackers/github.md`. Vendored `agent-security` and `owasp-security` untouched. `### \`op\`` headings in the adapters stay.
5. **Inventory after.** Add table 2 "After" with the same ids and the new file and section. Rules may differ only in location.
6. **Verify.** Pytest, shellcheck, `wc -c` before/after table for every touched file, total and Chief of Staff size.
7. **Closeout docs, PR, reviews** per `open-pr` and `security-review`.

Tests: only `test_section_pointers.py` is new (the spec asks for it). No existing test is edited.
