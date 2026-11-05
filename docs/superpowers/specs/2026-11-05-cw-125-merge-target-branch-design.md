# CW-125: Add a merge target branch setting

**Ticket:** [CW-125](https://github.com/collective-wisdom-org/collective-wisdom/issues/125)
**Status:** Shipped
**Shipped:** in PR #132, as specified

## Goal

An app can merge its PRs into a branch other than `main`, such as `dev`. A new `Merge target branch` row in `project.md` names it. A missing or unset row means `main`, so installed apps behave as today.

## Today

`main` is hardcoded on the app side:

- `scripts/merge_pr.py`: `gate()` refuses `baseRefName != "main"` and a root checkout not on `main`; `cleanup()` fast-forwards root `main`; the diff fetch and `publish_notes()` use `--base main` and `refs/remotes/origin/main`.
- `scripts/pr_diff_delta.py`, `scripts/review_scope.py` and `scripts/release_notes.py` fetch and diff against `refs/remotes/origin/main`.
- `scripts/cos_approve_pr.py` refuses a base other than `main`. `scripts/cos_brief.py` reads the migrations folder at `?ref=main` and says "head moved by merging main". `scripts/cos_rotation_check.py` rotates on a skill change only when the root checkout is on `main`.
- `project_config.approval_setting()` reads the `Approval risk tolerance` from `refs/remotes/origin/main`.
- The skills (`ship-loop`, `kickoff-feature`, `build-from-plan`, `open-pr`, `merge-pr`, `security-review`, `chief-of-staff` and its `startup.md`, `rotation.md`, `ticket-helper.md`, `approvals.md`), a few role docs under `agent-team/docs/agents/` and the template's Repo invariants all say `main`.

## Change

### Setting

- Add a row to § Git and GitHub in `agent-team/templates/project.md` and in this repo's `docs/agents/project.md`:

  ```
  | Merge target branch | `main`. The branch every PR merges into. The root checkout stays on it. Unset means `main` |
  ```

  This repo sets it to `main`.
- `project_config.target_branch()` returns the row's value, or `main` when the row is missing or has no backticked value. A value that is not a plain branch name stops the script with `SystemExit` (the same as a bad `Issue identifier prefix`). A plain name: letters, digits, `.`, `_`, `-` and `/`; no leading `-`, `/` or `.`; no trailing `/`, `.` or `.lock`; no `..` or `//`. Validation runs before the name reaches any git or `gh` argument.

### Scripts

Every app-side `main` reads `target_branch()`:

- `merge_pr.py` and `cos_approve_pr.py`: an invalid `Merge target branch` row stops the script with its message (`merge-pr: stop #N: ...`, exit 1; `cos-approve: cannot read the Merge target branch row of project.md`, exit 2) instead of escaping as a traceback.
- `merge_pr.py`: the base check (`base is X, not <target>`), the root checkout check and the fast-forward in `cleanup()`, the fetch before the diff compare, and `publish_notes()` (`--base <target>`, `refs/remotes/origin/<target>`). Messages name the target.
- `pr_diff_delta.py`, `review_scope.py`, `release_notes.py`: the ref becomes `refs/remotes/origin/<target>` and the fetch refspec `+refs/heads/<target>:refs/remotes/origin/<target>`. Docstrings say "the merge target branch".
- `cos_approve_pr.py`: the base check uses the target.
- `cos_brief.py`: `?ref=<target>` for the migrations folder, and the moved line says "merging <target>". The `Head moved to` regexes don't mention `main`, so they stay.
- `cos_rotation_check.py`: rotate on a skill change when the root checkout is on the target.
- `project_config.approval_setting()` reads `refs/remotes/origin/<target>:docs/agents/project.md`, with two extra guards so a branch an agent can push cannot become the trusted source (see Calls I made). The target and the branch pattern head come from the root checkout's `project.md` (the first entry of `git worktree list`, as `merge_pr.read_facts` finds it), never from the worktree the script runs in, so a PR cannot edit the `Merge target branch` row to redirect it. Failing to find or read that file gives `strict`:
  - the target must not start with the branch pattern head (`feat/` by default), and
  - the committed file on `origin/<target>` must name the same target (or no target, when the target is `main`).

  Either guard failing, like any other failed read, gives `strict` with the reason.
- Unchanged: `install.sh`, `tag-release.sh` and `scripts/agent-team-update.sh` keep reading collective-wisdom's own `origin/main`. `agent_usage.py` says "main checkout", which is not a branch.

### Skills and docs

Where a skill, `agent-team/docs/agents/*.md` or the template means the merge branch, it says "the merge target branch" (the `Merge target branch` row of `project.md`, default `main`) in place of `main`:

- `ship-loop`: the Spec stage branches from `origin/<target>`; the head-moved note reads `Head moved to <head> by merging <target>; ...`; Repo invariants say the root checkout stays on the target and nothing pushes to it.
- `kickoff-feature`, `build-from-plan`, `open-pr`, `merge-pr`, `security-review`, `chief-of-staff` (`SKILL.md`, `startup.md`, `rotation.md`, `ticket-helper.md`, `approvals.md`), and role docs such as `code-review.md`, `security-review.md`, `documenter.md`, `chief-of-staff.md`, `org-chart.md`, `github-auth.md` where they mean the merge branch.
- `agent-team/templates/project.md` § Repo invariants: "The root checkout stays on the merge target branch" and "Never push to the merge target branch".
- Mentions of collective-wisdom's own `main` (installer, release tags, the `release-notes` branch exception) stay as they are.

### Tests

- `test_project_config.py`: one table-driven test for `target_branch()`: missing row, unset (`none`, empty, `TODO(...)`), set (`dev`, `release/next`), invalid (`-x`, `a..b`, `dev.lock`, `a b`, `feat//x`).
- `test_project_config.py`: extend the existing `approval_setting` table with the target cases: target `dev` read from `origin/dev`, a target under `feat/` gives strict, a committed file that names a different target gives strict.
- `test_merge_pr.py`: one table-driven test for the base and root branch checks in `gate()` with the row set to `dev` (base `dev` passes, base `main` refused, root on `main` refused) and with no row (today's behavior).
- The existing suites must pass unchanged, which proves the default.

## Acceptance

- With the row set to `dev`, `merge_pr.py` accepts a PR whose base is `dev`, refuses one whose base is `main`, and fast-forwards a root checkout on `dev`.
- With no row, every script and skill behaves as today.
- `grep -nw main agent-team/scripts/*.py` outside the tests finds only the `target_branch()` default and text that is not about the branch (the "main checkout" wording, `__main__`, `def main`).
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.

## Calls I made

- **The approval setting follows the target, with guards.** The ticket doesn't say where the `Approval risk tolerance` is read once the target isn't `main`. Reading it from `origin/main` would leave a `dev` app reading a stale or missing row. Reading it from `origin/<target>` with the target taken from a feature worktree would let a branch point the target at a branch an agent can push. So the target comes from the root checkout's `project.md`, it must not be a `feat/` branch, and the committed file on that branch must name itself as the target. Any doubt reads as `strict`. This repo is `strict` either way.
- **An invalid value stops the script.** It does not fall back to `main`, because merging into the wrong branch is worse than stopping.
- **The head-moved note names the target** ("by merging dev"). The parsers only match `Head moved to ... unchanged since ...`, so old notes that say "main" still count.
- **`cos_rotation_check.py` uses the target too.** It isn't in the ticket's list of scripts, but it checks the root checkout's branch, which is now the target.
- **This PR touches the approval path** (`scripts/`, `docs/agents/project.md`, the template), so neither the spec nor the merge can be auto-approved.
- **Overlap with other open tickets.** CW-58 (team mode) and CW-126 (review mode) edit `ship-loop`, `open-pr`, `merge-pr`, `chief-of-staff` and `scripts/merge_pr.py`. The edits here are word swaps (`main` to the target) plus small changes in `merge_pr.py` `gate()`, `cleanup()` and `publish_notes()`. Whichever merges second rebases and keeps both.

## Out of scope

- Release branches or more than one target per repo.
- Changing collective-wisdom's own branch or how apps fetch a release from it.
