# CW-319 plan: warn when the Branch pattern row does not parse

Spec: `docs/superpowers/specs/2026-11-14-cw-319-warn-branch-pattern-design.md` (approved). Follow its Design steps 1 to 6. Test budget: `AGENTS.md` § Testing, one table-driven test per rule; test lines do not exceed feature lines.

## Task 1: project_config
Move the parse of the pattern into a helper that returns the heads or `None` when nothing parsed. `branch_heads()` uses it, prints `branch_pattern_error()`'s message to stderr once per process (module flag) when a bad row made it fall back, and still returns `("feat/",)`. Add `branch_pattern_error(rows=None)`: `None` for a missing, empty or `TODO(` row or a row that parses, else the one-line message from spec step 1. Parse rules and fallback value do not change.
Test: one table in `test_project_config.py` (prose with no backticks, token with no `<prefix>`, bad brace list, valid brace, valid plain head, missing, empty, TODO) with expected heads and whether stderr warns; one case calling `branch_heads()` twice on a bad row warns once.
Verify: `python3 -I -m pytest -q agent-team/scripts/test_project_config.py`

## Task 2: setup_repo
`unset_rows()` appends `Branch pattern` when `branch_pattern_error(rows)` is set (not via `branch_heads`, so status prints no stderr warning). `repair()`/`_merge` replace a Branch pattern row that does not parse with the template's row (heads `{feat,infra}/` and its note), as a placeholder row is filled; a valid row is left alone. Check how `_ph`/`PLACEHOLDER` treat the template row's `<prefix>` and make the replacement work.
Test in `test_setup_repo.py`: two `STATUS` rows (prose Branch pattern gives `placeholders: Branch pattern`; valid brace row gives `set`), one `write` case (re-setup replaces a prose row with the template row, leaves a valid row alone, and a second `status` then reports `set`).
Verify: `python3 -I -m pytest -q agent-team/scripts/test_setup_repo.py`

## Task 3: setup.md
One sentence in the `placeholders` paragraph of `agent-team/.claude/skills/chief-of-staff/setup.md` (spec step 5). Plain sentences, no em dashes.

## Final
`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`. Spec `Status:` stays Proposed until closeout (open-pr).
