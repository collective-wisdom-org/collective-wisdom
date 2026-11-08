#!/usr/bin/env python3
"""Say whether a PR's own changes are the same at two heads (e.g. after the merge target branch was merged in), or changed only in docs files.

Usage:
    ~/.collective-wisdom/scripts/pr_diff_delta.py <PR number> <reviewed SHA> [<head SHA>]

The reviewed SHA (40 hex) is the head the PASS reviews were posted on. The head
defaults to the PR's current headRefOid. The PR's diff at each head is taken against
that head's own merge base with origin/<merge target branch> (by its full ref name), and compared per file by blob IDs and modes
(`git diff --raw`), so any byte that differs, in either the base or the head blob, counts.

A docs file is an ASCII-named .md file that is README.md at the repo top, or under docs/ but not under docs/agents/ (compared
without regard to case), has no path part starting with "." and is not named CLAUDE.md, CLAUDE.local.md or AGENTS.md (any
case), and is a regular file (mode 100644, or absent) on both sides. review_scope.py uses the same rule.

Exit 0, last line (full SHAs):
  pr-diff-delta: same since <reviewed> at <head>
  pr-diff-delta: docs since <reviewed> at <head>: <file>, ...   files differ and every one is a docs file (same file format as changed)
  pr-diff-delta: changed since <reviewed> at <head>: <file>, <file>, ... (quoted with repr; first 10, then "... N more")
Exit 2: bad arguments or a read failed. Last line: pr-diff-delta: cannot <what>
Exit 2 means "could not tell": run the reviews.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402

ROOT = root()
GH = str(Path(__file__).absolute().parent / "gh.sh")
SHOW = 10
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


def show(files):
    """The files as repr, comma-separated: the first SHOW, then ", ... N more"."""
    return ", ".join(repr(f) for f in files[:SHOW]) + (f", ... {len(files) - SHOW} more" if len(files) > SHOW else "")


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
    """Fetch the merge target branch (forced, no tags) and the PR head so origin/<target> and both heads are local."""
    target = project_config.target_branch()
    run(["git", "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "origin", f"+refs/heads/{target}:{project_config.target_ref()}", f"pull/{pr}/head"])


def raw_entries(sha, run):
    """Return {path: (old mode, new mode, old blob, new blob)} for the PR's diff at sha, against sha's merge base with origin/<target>."""
    base = run(["git", "merge-base", project_config.target_ref(), sha]).strip()
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
    """Return ("same", []), ("docs", files) or ("changed", files). Raises CmdError when it can't compare.

    "docs": files differ and every differing file is a docs file on its modes at both heads. A head with no entry for a
    file has it unchanged against its base there, so the other head's entry gives the modes. Expects origin/<target> and
    both commits to be local already.
    """
    shas = [run(["git", "rev-parse", "--verify", f"{s}^{{commit}}"]).strip() for s in (reviewed, head)]
    old, new = (raw_entries(s, run) for s in shas)
    files = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))
    if not files:
        return "same", []
    docs = all(is_docs(p, [m for e in (old, new) if p in e for m in e[p][:2]]) for p in files)
    return ("docs" if docs else "changed"), files


def main(argv, run=run):
    if (
        not 2 <= len(argv) <= 3
        or not re.fullmatch(r"[0-9]+", argv[0])
        or not all(re.fullmatch(r"[0-9a-fA-F]{40}", a) for a in argv[1:])
    ):
        print("pr-diff-delta: cannot read arguments; usage: ~/.collective-wisdom/scripts/pr_diff_delta.py <PR number> <reviewed SHA, 40 hex> [<head SHA, 40 hex>]")
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
        print(f"pr-diff-delta: {kind} {tail}: {show(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
