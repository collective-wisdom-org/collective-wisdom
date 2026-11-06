#!/usr/bin/env python3
"""Say how much review a PR head needs: docs-only, small or full.

Usage:
    scripts/review_scope.py <PR number> [<head SHA>]
    scripts/review_scope.py --ci <base rev> <head rev>

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

SMALL_MAX = 200  # changed lines outside docs files; the one constant to tune
AGENT_CONFIG = ("claude.md", "claude.local.md", "agents.md")  # lowercase: tools read these from subfolders
REGULAR = ("100644", "000000")  # 000000: the file is absent on that side


def is_docs(path, modes):
    low = path.lower()  # case-insensitive checkouts: docs/Agents/ lands on docs/agents/
    in_docs = path == "README.md" or (low.startswith("docs/") and not low.startswith("docs/agents/"))
    # ASCII only: a lookalike such as docs/agentſ/ also lands on docs/agents/ on a case-insensitive checkout
    parts = low.split("/")
    # Agent config is not a record: hidden folders (docs/.claude/skills/) and CLAUDE.md or AGENTS.md at any depth
    config = any(p.startswith(".") for p in parts) or parts[-1] in AGENT_CONFIG
    return path.isascii() and path.endswith(".md") and in_docs and not config and all(m in REGULAR for m in modes)


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
        print("ci-scope: cannot read arguments; usage: scripts/review_scope.py --ci <base rev> <head rev>")
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
    if not 1 <= len(argv) <= 2 or not re.fullmatch(r"[0-9]+", argv[0]) or not all(re.fullmatch(r"[0-9a-fA-F]{40}", a) for a in argv[1:]):
        print("review-scope: cannot read arguments; usage: scripts/review_scope.py <PR number> [<head SHA, 40 hex>]")
        return 2
    pr = argv[0]
    try:
        head = argv[1].lower() if len(argv) == 2 else run([GH, "pr", "view", pr, "--json", "headRefOid", "-q", ".headRefOid"]).strip()
        fetch(pr, run)
        kind, detail = classify(head, run)
        head = run(["git", "rev-parse", "--verify", f"{head}^{{commit}}"]).strip()
    except CmdError as e:
        print(f"review-scope: cannot classify #{pr}: {e}")
        return 2
    print(f"review-scope: {kind} at {head}: {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
