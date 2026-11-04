#!/usr/bin/env python3
"""Say how much review a PR head needs: docs-only, small or full.

Usage:
    scripts/review_scope.py <PR number> [<head SHA>]

The head (40 hex) defaults to the PR's current headRefOid. The PR's diff is taken at the head against its merge base
with origin/main (by its full ref name). A docs file is an ASCII-named .md file that is README.md at the repo top, or under docs/ but not
under docs/agents/ (compared without regard to case), and is a regular file (mode 100644, or absent) on both sides.
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
"""

import importlib.util
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "pr_diff_delta", Path(__file__).with_name("pr_diff_delta.py")
)
pr_diff_delta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr_diff_delta)
CmdError, MAIN, GH, fetch, run = (
    pr_diff_delta.CmdError, pr_diff_delta.MAIN, pr_diff_delta.GH, pr_diff_delta.fetch, pr_diff_delta.run
)

SMALL_MAX = 200  # changed lines outside docs files; the one constant to tune
REGULAR = ("100644", "000000")  # 000000: the file is absent on that side


def is_docs(path, modes):
    low = path.lower()  # case-insensitive checkouts: docs/Agents/ lands on docs/agents/
    in_docs = path == "README.md" or (low.startswith("docs/") and not low.startswith("docs/agents/"))
    # ASCII only: a lookalike such as docs/agentſ/ also lands on docs/agents/ on a case-insensitive checkout
    return path.isascii() and path.endswith(".md") and in_docs and all(m in REGULAR for m in modes)


def classify(head, run):
    """Return (kind, detail) for the PR's diff at head against its merge base with origin/main.

    Expects origin/main and head to be local already. Raises CmdError when it can't read the diff.
    """
    head = run(["git", "rev-parse", "--verify", f"{head}^{{commit}}"]).strip()
    base = run(["git", "merge-base", MAIN, head]).strip()
    flags = ["-z", "--no-renames", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none"]
    raw = run(["git", "diff", "--raw", *flags, base, head]).split("\0")
    stat = run(["git", "diff", "--numstat", *flags, base, head]).split("\0")
    modes = {}
    for meta, path in zip(raw[0::2], raw[1::2]):
        m = meta.lstrip(":").split()
        if len(m) != 5:
            raise CmdError(f"compare {path!r}: unexpected git diff --raw line")
        modes[path] = m[:2]
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


def main(argv, run=run):
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
