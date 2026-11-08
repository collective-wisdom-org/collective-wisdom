# CW-199 plan: run the docs check once, after the reviews pass

Spec: `docs/superpowers/specs/2026-11-08-cw-199-docs-check-once-design.md`. Tests per `AGENTS.md` § Testing: one table-driven test per rule. Task 1 (scripts) and Task 2 (skills and role docs) touch different files and are built in parallel.

## Task 1: scripts and tests

- `agent-team/scripts/pr_diff_delta.py`: `is_docs`, `AGENT_CONFIG`, `REGULAR` move here from `review_scope.py`; `delta()` returns `("same", [])`, `("docs", files)` or `("changed", files)`; the CLI prints `pr-diff-delta: docs since <reviewed> at <head>: <files>`; a `show()` helper formats the file list; module docstring updated.
- `agent-team/scripts/review_scope.py`: `is_docs` is `pr_diff_delta.is_docs`; no behavior change.
- `agent-team/scripts/merge_pr.py`: `stands` accepts `same` or `docs`; `NOTE` also matches `Head moved to <head>; PR diff changed only in docs files since <reviewed>: ...`; header text updated.
- `agent-team/scripts/review_gate.py`: on `docs`, builds that note and prints `review-gate: note head <head> reviewed <reviewed>`; `same` and `changed` unchanged; header `note` case updated.
- Tests: `test_pr_diff_delta.py` gains a `docs` row and a mixed docs-plus-code row (`changed`); new `test_docs_reviews_stand.py` builds a real git fixture and checks `review_gate.verdict` and `merge_pr.review` agree (docs-file fix gives `note`, then `pass`; skill, `docs/agents/` or `.py` fix gives `rerun both`).

## Task 2: skills and role docs (other implementer)

Spec § 5 text edits, under `agent-team/.claude/**` and `agent-team/docs/agents/**`:

- `open-pr`: § Docs check rewritten (runs once after both reviews, the `## Docs check` comment, once rule, conflict `on` exception); § Closeout docs sentence; § Agent review comment loop drops the docs result, the `Docs checked:` line and the Must fix sentence; § Done when; § Conflict resolution step 4; § CI review mode steps.
- `ship-loop`: § Phase gates, § Phases 3 and 4, `Docs checked` in `MERGE READY` from the `## Docs check` comment.
- `docs/agents/code-review.md`: § Method step 3 and the `Docs checked:` line go.
- `docs/agents/org-chart.md`: stage label and Documenter row.
- `.claude/agents/documenter.md` and `code-reviewer.md` descriptions.

## Verify

`python3 -I -m pytest -q agent-team/scripts` (`uvx pytest -q agent-team/scripts`) and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
