#!/usr/bin/env python3
"""Say whether a PR's own changes are the same at two heads (e.g. after main was merged in).

Usage:
    scripts/pr_diff_delta.py <PR number> <reviewed SHA> [<head SHA>]

The reviewed SHA (40 hex) is the head the PASS reviews were posted on. The head
defaults to the PR's current headRefOid. The PR's diff at each head is taken against
that head's own merge base with origin/main (by its full ref name), and compared per file by blob IDs and modes
(`git diff --raw`), so any byte that differs, in either the base or the head blob, counts.

Exit 0, last line (full SHAs):
  pr-diff-delta: same since <reviewed> at <head>
  pr-diff-delta: changed since <reviewed> at <head>: <file>, <file>, ... (quoted with repr; first 10, then "... N more")
Exit 2: bad arguments or a read failed. Last line: pr-diff-delta: cannot <what>
Exit 2 means "could not tell": run the reviews.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parent.parent
GH = str(ROOT / "scripts" / "gh.sh")
SHOW = 10
# Full ref name: a tag called origin/main would win over the short name.
MAIN = "refs/remotes/origin/main"


class CmdError(Exception):
    pass


def run(cmd):
    """Run a command in the repo and return its stdout as text; raise CmdError on failure.

    Read as bytes and decoded with surrogateescape, so no byte (a bare \\r, say) is rewritten.
    """
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True)
    if p.returncode:
        err = (p.stderr or p.stdout).decode("utf-8", "surrogateescape").strip()
        raise CmdError(err or f"exit {p.returncode}")
    return p.stdout.decode("utf-8", "surrogateescape")


def fetch(pr, run):
    """Fetch main (forced, no tags) and the PR head so MAIN and both heads are local."""
    run(["git", "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "origin", f"+refs/heads/main:{MAIN}", f"pull/{pr}/head"])


def raw_entries(sha, run):
    """Return {path: (old mode, new mode, old blob, new blob)} for the PR's diff at sha, against sha's merge base with origin/main."""
    base = run(["git", "merge-base", MAIN, sha]).strip()
    out = run(["git", "diff", "--raw", "-z", "--no-renames", "--no-abbrev", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none", base, sha])
    parts = out.split("\0")
    entries = {}
    for meta, path in zip(parts[0::2], parts[1::2]):
        m = meta.lstrip(":").split()
        if len(m) != 5:
            raise CmdError(f"compare {path!r}: unexpected git diff --raw line")
        entries[path] = tuple(m[:4])
    return entries


def delta(reviewed, head, run):
    """Return ("same", []) or ("changed", files). Raises CmdError when it can't compare.

    Expects origin/main and both commits to be local already.
    """
    shas = [run(["git", "rev-parse", "--verify", f"{s}^{{commit}}"]).strip() for s in (reviewed, head)]
    old, new = (raw_entries(s, run) for s in shas)
    files = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))
    return ("changed", files) if files else ("same", [])


def main(argv, run=run):
    if (
        not 2 <= len(argv) <= 3
        or not re.fullmatch(r"[0-9]+", argv[0])
        or not all(re.fullmatch(r"[0-9a-fA-F]{40}", a) for a in argv[1:])
    ):
        print("pr-diff-delta: cannot read arguments; usage: scripts/pr_diff_delta.py <PR number> <reviewed SHA, 40 hex> [<head SHA, 40 hex>]")
        return 2
    pr, reviewed = argv[0], argv[1].lower()
    try:
        head = argv[2].lower() if len(argv) == 3 else run([GH, "pr", "view", pr, "--json", "headRefOid", "-q", ".headRefOid"]).strip()
        fetch(pr, run)
        kind, files = delta(reviewed, head, run)
        reviewed, head = (run(["git", "rev-parse", "--verify", f"{s}^{{commit}}"]).strip() for s in (reviewed, head))
    except CmdError as e:
        print(f"pr-diff-delta: cannot compare #{pr}: {e}")
        return 2
    tail = f"since {reviewed} at {head}"
    if kind == "same":
        print(f"pr-diff-delta: same {tail}")
    else:
        shown = ", ".join(repr(f) for f in files[:SHOW]) + (f", ... {len(files) - SHOW} more" if len(files) > SHOW else "")
        print(f"pr-diff-delta: changed {tail}: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
