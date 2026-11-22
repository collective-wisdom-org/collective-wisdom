#!/usr/bin/env python3
"""Say how much review a PR head needs: docs-only, small or full.

Usage:
    ~/.collective-wisdom/scripts/review_scope.py <PR number> [<head SHA>] [--next]
    ~/.collective-wisdom/scripts/review_scope.py <PR number> <head SHA> --skip-comment <pass> [--next]
    ~/.collective-wisdom/scripts/review_scope.py --ci <base rev> <head rev>

The head (40 hex) defaults to the PR's current headRefOid. The PR's diff is taken at the head against its merge base
with origin/<merge target branch> (by its full ref name). A docs file is an ASCII-named .md file that is README.md at the repo top, or under docs/ but not
under docs/agents/ (compared without regard to case), has no path part starting with "." and is not named CLAUDE.md,
CLAUDE.local.md or AGENTS.md (any case), and is a regular file (mode 100644, or absent) on both sides.
Changed lines are added plus deleted lines over the files that are not docs files.

Classes, checked in this order:
  docs-only  at least one file changed, and every changed file is a docs file
  small      200 changed lines or fewer
  full       anything else, including any binary file outside the docs files

Exit 0, last line (full SHA):
  review-scope: docs-only at <head>: <N> files
  review-scope: small at <head>: <L> lines in <M> files
  review-scope: full at <head>: <L> lines in <M> files   (or ": binary <file>")
Exit 2: bad arguments or a read failed. Last line: review-scope: cannot <what>
Exit 2 means "could not tell": review as full.

--skip-comment <pass> (a whole number, 1 or more; the head SHA is required) is the docs-only security review skip comment of open-pr § Review scope. When the
class at the head is docs-only it prints the whole comment body and exits 0, and nothing else (the review-scope line is inside it):
  ## Security review (pass <pass>)
  <blank line>
  Skipped: docs-only diff. review-scope: docs-only at <head>: <N> files
  <blank line>
  Verdict: PASS
For any other class it prints the usual `review-scope:` line and exits 1: post nothing. Exit 2 as above.

--next prints `next: <instruction>` after the last line, from the NEXT table below: for each class line, for `cannot` (exit 2) and, with
--skip-comment, after the body (the body ends at its `Verdict: PASS` line; `next:` is not part of it). It is for the PR modes, not --ci.
Without --next the output is unchanged.

--ci is for the CI workflow. It diffs the two commits directly (no fetch, no merge base) and says which CI steps the
change needs. Tests are skipped only when at least one file changed and every changed file is a docs file, since no test
reads one. Shellcheck runs when any changed path ends in .sh, is under .github/ or is a .shellcheckrc or shellcheckrc.
Exit 0, last line:
  ci-scope: tests=run|skip shellcheck=run|skip
Exit 2: bad arguments or the diff failed. Last line: ci-scope: cannot <what>. The workflow then runs both.
"""

import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import project_config  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "pr_diff_delta", Path(__file__).with_name("pr_diff_delta.py")
)
pr_diff_delta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr_diff_delta)
CmdError, GH, fetch, run = (
    pr_diff_delta.CmdError, pr_diff_delta.GH, pr_diff_delta.fetch, pr_diff_delta.run
)

# --next: the instruction after each PR-mode output line. {n} and {head} are filled from the call. Where open-pr § Review scope used to hold this table.
NEXT = {
    "docs-only": "run the code review as usual. After its PASS, run ~/.collective-wisdom/scripts/review_scope.py {n} {head} --skip-comment <pass> (the head the code review passed on); "
                 "only when it exits 0, post its output as a PR comment with ~/.collective-wisdom/scripts/gh.sh pr comment {n} --body-file <file> and keep the URL. No security subagent run.",
    "small": "one `code-reviewer` subagent reviews the diff once with both briefs: the code review brief and the Custom Instructions list of security-review § Primary review path "
             "(~/.collective-wisdom/docs/agents/code-review.md § Small diffs). Post `## Code review (pass N)` as code-reviewer and `## Security review (pass M)` as security-reviewer. "
             "On either CHANGES NEEDED, fix, push, wait for CI and run the next combined pass. Both loops end when both latest verdicts are PASS on the same head.",
    "full": "run the code review loop, then the security review loop (open-pr § Agent review comment loop, security-review).",
    "skip": "post the comment above as a PR comment with ~/.collective-wisdom/scripts/gh.sh pr comment {n} --body-file <file>, keep its URL, and go on to the docs check.",
    "cannot": "it could not tell: run it once more; if that also fails, review as `full`.",
    "args": "fix the call: review_scope.py <PR number> [<head SHA>] [--next].",
}

SMALL_MAX = 200  # changed lines outside docs files; the one constant to tune
is_docs = pr_diff_delta.is_docs  # the rule lives in pr_diff_delta.py


DIFF_FLAGS = ["-z", "--no-renames", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none"]


def changed_modes(base, head, run):
    """Return {path: [old mode, new mode]} for the diff from base to head. Raises CmdError when it can't read it."""
    raw = run(["git", "diff", "--raw", *DIFF_FLAGS, base, head]).split("\0")
    modes = {}
    for meta, path in zip(raw[0::2], raw[1::2]):
        m = meta.lstrip(":").split()
        if len(m) != 5:
            raise CmdError(f"compare {path!r}: unexpected git diff --raw line")
        modes[path] = m[:2]
    return modes


def ci_scope(base, head, run):
    """Return (tests, shellcheck), each "run" or "skip", for the diff from base to head. Raises CmdError."""
    base, head = (run(["git", "rev-parse", "--verify", f"{r}^{{commit}}"]).strip() for r in (base, head))
    modes = changed_modes(base, head, run)
    docs_only = bool(modes) and all(is_docs(p, m) for p, m in modes.items())
    lint = any(p.endswith(".sh") or p.startswith(".github/") or p.rsplit("/", 1)[-1] in (".shellcheckrc", "shellcheckrc") for p in modes)
    return ("skip" if docs_only else "run"), ("run" if lint else "skip")


def classify(head, run):
    """Return (kind, detail) for the PR's diff at head against its merge base with origin/<merge target branch>.

    Expects origin/<target> and head to be local already. Raises CmdError when it can't read the diff.
    """
    head = run(["git", "rev-parse", "--verify", f"{head}^{{commit}}"]).strip()
    base = run(["git", "merge-base", project_config.target_ref(), head]).strip()
    modes = changed_modes(base, head, run)
    stat = run(["git", "diff", "--numstat", *DIFF_FLAGS, base, head]).split("\0")
    docs = {p for p, m in modes.items() if is_docs(p, m)}
    if modes and len(docs) == len(modes):
        return "docs-only", f"{len(docs)} files"
    lines, files = 0, 0
    for entry in stat:
        if not entry:
            continue
        added, deleted, path = entry.split("\t", 2)
        if path in docs:
            continue
        if "-" in (added, deleted):
            return "full", f"binary {path!r}"
        lines += int(added) + int(deleted)
        files += 1
    return ("small" if lines <= SMALL_MAX else "full"), f"{lines} lines in {files} files"


def main_ci(argv, run):
    if len(argv) != 2 or any(not a or a.startswith("-") for a in argv):
        print("ci-scope: cannot read arguments; usage: ~/.collective-wisdom/scripts/review_scope.py --ci <base rev> <head rev>")
        return 2
    try:
        tests, shellcheck = ci_scope(*argv, run)
    except CmdError as e:
        print(f"ci-scope: cannot diff {argv[0]}..{argv[1]}: {e}")
        return 2
    print(f"ci-scope: tests={tests} shellcheck={shellcheck}")
    return 0


def main(argv, run=run):
    if argv[:1] == ["--ci"]:
        return main_ci(argv[1:], run)
    want_next = "--next" in argv
    argv = [a for a in argv if a != "--next"]
    skip = None
    if "--skip-comment" in argv:
        i = argv.index("--skip-comment")
        skip = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
        if not re.fullmatch(r"[1-9][0-9]*", skip) or len(argv) != 2:
            skip = False
    ok = skip is not False and 1 <= len(argv) <= 2 and re.fullmatch(r"[0-9]+", argv[0]) and all(re.fullmatch(r"[0-9a-fA-F]{40}", a) for a in argv[1:])
    if not ok:
        print("review-scope: cannot read arguments; usage: ~/.collective-wisdom/scripts/review_scope.py <PR number> [<head SHA, 40 hex>] [--next] "
              "| <PR number> <head SHA> --skip-comment <pass> [--next]")
        if want_next:
            print(f"next: {NEXT['args']}")
        return 2
    pr = argv[0]
    try:
        head = argv[1].lower() if len(argv) == 2 else run([GH, "pr", "view", pr, "--json", "headRefOid", "-q", ".headRefOid"]).strip()
        fetch(pr, run)
        kind, detail = classify(head, run)
        head = run(["git", "rev-parse", "--verify", f"{head}^{{commit}}"]).strip()
    except CmdError as e:
        print(f"review-scope: cannot classify #{pr}: {e}")
        if want_next:
            print(f"next: {NEXT['cannot']}")
        return 2
    line = f"review-scope: {kind} at {head}: {detail}"
    if skip and kind == "docs-only":
        print(f"## Security review (pass {skip})\n\nSkipped: docs-only diff. {line}\n\nVerdict: PASS")
        if want_next:
            print(f"next: {NEXT['skip'].format(n=pr, head=head)}")
        return 0
    print(line)
    if want_next:
        print(f"next: {NEXT[kind].format(n=pr, head=head)}")
    return 1 if skip else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
