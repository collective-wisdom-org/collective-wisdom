# CW-102: Skip the test and lint steps on docs-only changes

**Ticket:** [CW-102](https://github.com/collective-wisdom-org/collective-wisdom/issues/102)
**Status:** Shipped
**Shipped:** in PR #121, as specified

## Goal

A PR that changes only docs gets a green `script-tests` and a green `shellcheck` check in seconds, without installing Python, running pytest or running shellcheck. Any PR that could break a test or a shell script still runs the full step.

## Today

Facts from `main` at `41386ee`, checked 2026-11-04.

- `.github/workflows/ci.yml` has two jobs, `script-tests` (checkout, setup-python, `pip install pytest`, pytest) and `shellcheck` (checkout, shellcheck). It runs on every `pull_request` and every push to `main`, with no path filter.
- `docs/agents/project.md` names `script-tests` and `shellcheck` as the required checks.
- `scripts/merge_pr.py` refuses to merge when the PR has no checks. `OK_CONCLUSIONS` is `SUCCESS`, `SKIPPED`, `NEUTRAL`. `scripts/wait-for-ci.sh` waits for a check row and exits 2 if none appears.
- Several tests read real files outside `agent-team/scripts/`: `test_section_pointers.py` and `test_tracker_docs.py` read every skill under `.claude/skills/`, `docs/agents/` and `templates/`; `test_agent_files.py` reads `.claude/agents/`; `test_root_links.py` checks the root links and `docs/agents/`. So an edit to a skill or a role doc can turn pytest red with no `.py` change.
- No test reads `README.md` or anything under `docs/` other than `docs/agents/`.
- `agent-team/scripts/review_scope.py` (CW-54) already defines a docs file: an ASCII `.md` file that is `README.md` at the top or sits under `docs/` but not `docs/agents/`, is not `CLAUDE.md` or `AGENTS.md`, has no hidden path part, and is a regular file. Its `is_docs` is the set of files no test reads.

## Change

### `agent-team/scripts/review_scope.py`: a `--ci` mode

`scripts/review_scope.py --ci <base SHA> <head SHA>` diffs the two commits (same `git diff --raw` flags as `classify`) and prints one last line:

```
ci-scope: tests=run|skip shellcheck=run|skip
```

- `tests=skip` only when at least one file changed and every changed file passes `is_docs`. Anything else, skill and role-doc edits included, runs the tests.
- `shellcheck=run` when any changed path ends in `.sh`, sits under `.github/`, or is named `.shellcheckrc` or `shellcheckrc` (shellcheck reads those). `install.sh` and `tag-release.sh` are covered by the `.sh` rule.
- A bad argument or a failed git call: exit 2 with `ci-scope: cannot <what>`. The workflow then runs both.

The docs rule lives in `is_docs` only, so review scope and CI agree on what docs-only means.

### `.github/workflows/ci.yml`

Both jobs keep their names and still run on every PR and push, so both checks always show up.

- Checkout gets `fetch-depth: 2`. On `pull_request` the runner checks out GitHub's merge commit, so `HEAD^1` is the base tip and `HEAD^1..HEAD` is exactly what the PR changes on `main`.
- A first step, `scope`, runs with the runner's own `python3` (no setup-python). On `pull_request` it runs `python3 agent-team/scripts/review_scope.py --ci HEAD^1 HEAD` and writes `tests` and `shellcheck` to `$GITHUB_OUTPUT`. It prints the `ci-scope:` line to the log. If the event isn't `pull_request`, or the script exits non-zero or prints no `ci-scope:` line, both outputs are `run`.
- `script-tests`: setup-python, `pip install pytest` and pytest each get `if: steps.scope.outputs.tests == 'run'`.
- `shellcheck`: the shellcheck step gets `if: steps.scope.outputs.shellcheck == 'run'`.
- Skipped steps leave the job's conclusion `SUCCESS`, so `merge_pr.py`, `wait-for-ci.sh` and the branch ruleset see two green checks.

### Tests: `agent-team/scripts/test_review_scope.py`

One table-driven test for `--ci` against a temp git repo, as the existing classify test does:

- `docs/superpowers/specs/a.md` only: tests skip, shellcheck skip;
- `README.md` plus `docs/x.md`: skip, skip;
- a skill `.md` under `.claude/skills/`: tests run, shellcheck skip;
- `docs/agents/x.md`: tests run, shellcheck skip;
- `install.sh`: run, run;
- `agent-team/scripts/x.py`: run, skip;
- `.github/workflows/ci.yml`: run, run;
- a bad SHA: exit 2.

## Acceptance

- A docs-only PR shows green `script-tests` and `shellcheck` checks whose logs show `tests=skip shellcheck=skip` and no pytest or shellcheck step run.
- A PR touching a `.py` file runs pytest; a PR touching a `.sh` file runs both. This PR (it changes `.py` and the workflow) runs both.
- `scripts/wait-for-ci.sh` exits 0 on the docs-only PR. `scripts/merge_pr.py` accepts its checks (both `SUCCESS`).

Check during build: open a draft probe PR from a `feat/cw-102-probe` branch, based on this branch, that changes one file under `docs/superpowers/`, into `feat/cw-102-skip-ci-on-docs-only`. The `pull_request` trigger has no branch filter, so it runs the new workflow. Run `wait-for-ci.sh` on it, read the job logs, then close it and delete the branch.

## Leaves out

- Merging the two jobs (#100), cancelling superseded runs (#101), the push-to-main run (#103).
- Any change to `merge_pr.py`, `wait-for-ci.sh` or the required check names.
- Skipping CI on push to `main`: those runs keep running everything.

## Calls I made

- **Tests still run on skill and role-doc edits.** The ticket says to skip pytest unless a `.py`, `.sh`, `agent-team/scripts/**` or workflow file changes. That would let a skill edit that breaks `test_section_pointers.py` or `test_tracker_docs.py` merge green. Pytest skips only on the CW-54 docs files (`README.md` and `docs/` outside `docs/agents/`), which no test reads. Shellcheck follows the ticket's narrower rule, since it reads only `.sh` files. Skill-only PRs therefore still install Python and run pytest, so the saving is smaller than the ticket's 14 of 30.
- **The rule lives in `review_scope.py`, not inline in the workflow.** One definition of docs-only, and a test can cover it. The cost is one more mode on that script, which also ships to apps (harmless there).
- **Skip at the step level, not the job level.** The jobs still run and finish `SUCCESS`, rather than reporting `SKIPPED`. Both scripts accept either, but `SUCCESS` matches what a reader expects of a green check and needs no extra job.
- **The scope step is copied into both jobs** rather than run in a third job. A third job would bill another minute per run, which #100 is trying to cut. #100 merges the jobs later, which removes the copy.
- **No third-party path-filter action.** A plain `git diff` on the merge commit, no new dependency.
- **Anything unsure runs everything:** a push to `main`, a non-PR event, a script error.
- **A PR can change its own CI.** The scope script and workflow come from the PR head, so a PR could edit them to skip its own tests. That is true of the workflow today; code review catches it.
- **Probe PR to prove the docs-only path**, closed and deleted after.
