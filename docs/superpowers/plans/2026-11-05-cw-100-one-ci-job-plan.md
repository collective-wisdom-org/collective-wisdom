# CW-100: one CI job plan

Spec: [2026-11-05-cw-100-one-ci-job-design.md](../specs/2026-11-05-cw-100-one-ci-job-design.md)

## Task 1: merge the jobs in `.github/workflows/ci.yml`

Replace the `script-tests` and `shellcheck` jobs with one job `checks` on `ubuntu-latest`. Leave the header, concurrency block and `mod-tests` unchanged.

Steps, in order:
1. `actions/checkout@v4` with `fetch-depth: 2`.
2. `ci scope` step, copied once from the existing jobs (id `scope`).
3. `shellcheck`: `if: steps.scope.outputs.shellcheck == 'run'`, run `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
4. `actions/setup-python@v5` (3.12), `pip install pytest` and `python3 -m pytest -q agent-team/scripts`, each with `if: ${{ !cancelled() && steps.scope.outputs.tests == 'run' }}`.

Give the shellcheck and pytest steps a `name:`.

## Task 2: `docs/agents/project.md`

The `Required CI checks` row value becomes `checks`. Nothing else.

## Verify

- `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` parses.
- `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` and `python3 -I -m pytest -q agent-team/scripts` pass locally.
- After the PR opens: green run on this head; two throwaway commits (shellcheck error, failing test) each turn `checks` red at the right step, then are reverted. Links go in the PR's Proof section.

No new tests: no script or behavior changes (`AGENTS.md` § Testing).
