# CW-102 plan: skip tests and lint on docs-only changes

Spec: [design](../specs/2026-11-04-cw-102-skip-ci-on-docs-only-design.md)

1. `agent-team/scripts/review_scope.py`: add `--ci <base> <head>` mode. It diffs the two commits with the same `git diff --raw` flags as `classify`, then prints `ci-scope: tests=run|skip shellcheck=run|skip`. `tests=skip` only when files changed and all pass `is_docs`. `shellcheck=run` when any path ends in `.sh`, starts with `.github/` or is named `.shellcheckrc` or `shellcheckrc`. Bad args or a git failure: exit 2, `ci-scope: cannot <what>`. Existing PR-number mode is unchanged.
2. `agent-team/scripts/test_review_scope.py`: one table-driven test for `--ci` against a temp repo (cases in the spec), plus exit 2 on a bad SHA.
3. `.github/workflows/ci.yml`: `fetch-depth: 2`, a `scope` step per job (PR events only, fallback both `run`), and `if:` on the setup-python, pip, pytest and shellcheck steps.
4. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
