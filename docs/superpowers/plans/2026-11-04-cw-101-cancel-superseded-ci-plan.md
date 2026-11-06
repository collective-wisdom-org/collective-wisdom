# CW-101 plan: cancel superseded CI runs on the same PR

Spec: [2026-11-04-cw-101-cancel-superseded-ci-design.md](../specs/2026-11-04-cw-101-cancel-superseded-ci-design.md). The workflow is at the repo root, not under `agent-team/`, so edit `.github/workflows/ci.yml` in place.

1. `.github/workflows/ci.yml`: add the `concurrency` block from the spec's § Change between `on:` and `jobs:`, comment line included, exactly as written there. Change nothing else in the file.
2. No test file (the change is workflow config; `AGENTS.md` § Testing).
3. Verify: the file parses as YAML and has top-level keys `name`, `on`, `concurrency`, `jobs` (`python3 -c 'import yaml'` if available, otherwise `ruby -ryaml`); `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`; `python3 -I -m pytest -q agent-team/scripts`.
4. Open the PR, then prove it live per the spec's § Proof: push two commits to the branch a few seconds apart and show the older run `cancelled`; run `./scripts/wait-for-ci.sh <N>` and show `pass`. Quote the `group` expression and its two keys on `push`. Then closeout docs, docs check, code review and security review per ship-loop.
