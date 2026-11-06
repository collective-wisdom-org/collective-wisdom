# CW-126 plan: review mode setting that uses CI review instead of the agent reviewers

Spec: [2026-11-05-cw-126-ci-review-mode-design.md](../specs/2026-11-05-cw-126-ci-review-mode-design.md). All paths below are under `agent-team/`. Follow the spec's § Design for every detail (output lines, exit codes, error wording). Open PRs #131 (CW-58) and #132 (CW-125) edit the same skills and `merge_pr.py`: add new sections and small hunks, don't reflow existing text.

## A. Scripts and tests

1. `templates/project.md`: new `## Review` section after `## Commands` with the three rows from the spec.
2. `scripts/project_config.py`: `review_mode()` (row `Review mode`: missing or unset gives `agents`; `ci` or `agents`; any other value raises `SystemExit` with a `project.md:` message) and `ci_bot()` (row `CI review bot login`, `[bot]` suffix removed, lower case, None when unset).
3. `scripts/ci_review.py` (new, executable): `list <N>` and `resolve <thread id>` per the spec. One paginated GraphQL call through `scripts/gh.sh api graphql`; a pure `classify(threads, bot)` function holds the logic so the test needs no gh. Output holds only paths, line numbers, pattern-checked URLs and ids.
4. `scripts/merge_pr.py`: `read_facts` stores `f["reviewMode"]` and, in `ci` mode, `f["ciThreads"]` (unresolved bot threads) and `f["ciBot"]`. `gate()` in `ci` mode skips the two review checks and stops with the spec's two messages. A bad `Review mode` value makes `read_facts` raise (exit 2 path in `main`). Keep the diff to a few hunks.
5. `scripts/cos_brief.py` `pr`, `scripts/cos_handoff.py`, `scripts/cos_ready_check.py`: the `ci` variants from the spec. `cos_ready_check` adds `statusCheckRollup` to its PR list fields only if needed for the green-checks test, and keeps fixtures working.
6. Tests, one table-driven test per rule in the existing files (new `scripts/test_ci_review.py` for classification): `gate()` mode switch, `ci_review` classification, brief and handoff lines in both modes, ready check in `ci` mode. Test lines stay below feature lines. Also check `test_install.py` and `test_root_links.py` still pass (the new script must ship).

## B. Docs (prose, no tests)

7. `.claude/skills/ship-loop/SKILL.md`: `Review mode` paragraph under § Phase gates; § Team mode `MERGE READY` variant for `ci` mode (the CI and CI review lines, and the no-head-moved-exception sentence).
8. `.claude/skills/open-pr/SKILL.md`: `## CI review mode` section replacing § Review scope and § Agent review comment loop when the mode is `ci`.
9. `.claude/skills/security-review/SKILL.md`: one line that the phase doesn't run in `ci` mode. `.claude/skills/merge-pr/SKILL.md`: checks list gets the `ci` variant. `docs/agents/code-review.md`, `docs/agents/security-review.md`, `docs/agents/org-chart.md`: a line each only if they would otherwise say the agent reviewers always run.
10. `.claude/skills/chief-of-staff/approvals.md` (On `MERGE READY` step 2 and the merge block's `Reviews:` line) and `.claude/skills/chief-of-staff/SKILL.md` (restart message): the `ci` variant.
11. `README.md` / `docs/agents/README.md`: mention the setting only where settings are listed.

## Verify

`python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`. Then open the PR with `Refs #126` (the real-bot run is Not proven), closeout docs, docs check, code review and security review per ship-loop § Team mode. In `agents` mode (this repo) the existing review flow applies unchanged.
