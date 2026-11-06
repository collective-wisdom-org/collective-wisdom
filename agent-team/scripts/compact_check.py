#!/usr/bin/env python3
"""Say whether the compaction pass should run, and print the sizes it reports.

Usage:
    scripts/compact_check.py [--base <ref>]

Counts the markdown files agents load, under agent-team/: skills (not the vendored agent-security and
owasp-security), agents/*.md, docs/agents/**/*.md and templates/AGENTS.md. The change set is the counted files
that differ between the merge base of the base ref (default: the merge target branch from project.md) and the
working tree, plus untracked ones. Size is characters of the decoded text; a missing file is 0.

Output: one `<path> <before> <after> <+/-delta>` line per file, a `total` line, then the last line:
  compact: run (+<net> characters)       the net change is above 0
  compact: skip (<reason>)               no agent files changed, net <delta> characters, or not collective-wisdom
Exit 0 for run and skip. Exit 2 when git fails or the arguments are bad: compact: cannot read <what>
"""

import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402

ROOT = root()
VENDORED = ("agent-security", "owasp-security")


class CmdError(Exception):
    pass


def git(*args):
    """Run git in the repo and return stdout as text; raise CmdError on failure."""
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if p.returncode:
        raise CmdError((p.stderr or p.stdout).decode("utf-8", "replace").strip() or f"exit {p.returncode}")
    return p.stdout.decode("utf-8", "surrogateescape")


def counted(path):
    p = PurePosixPath(path)
    if p.suffix != ".md" or p.parts[:1] != ("agent-team",):
        return False
    rest = p.parts[1:]
    if rest[:2] == (".claude", "skills"):
        return len(rest) > 3 and rest[2] not in VENDORED
    if rest[:2] == (".claude", "agents"):
        return len(rest) == 3
    return rest[:2] == ("docs", "agents") or rest == ("templates", "AGENTS.md")


def sizes(base):
    """Return [(path, before, after)] for the counted files in the change set, sorted by path."""
    mb = git("merge-base", base, "HEAD").strip()
    changed = git("diff", "--name-only", "-z", "--no-renames", mb).split("\0")
    changed += git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    rows = []
    for path in sorted({p for p in changed if counted(p)}):
        try:
            before = len(git("show", f"{mb}:{path}"))
        except CmdError:
            before = 0  # not in the base: a new file
        try:
            after = len((ROOT / path).read_bytes().decode("utf-8", "surrogateescape"))
        except OSError:
            after = 0  # deleted
        rows.append((path, before, after))
    return rows


def main(argv):
    if argv and (argv[0] != "--base" or len(argv) != 2):
        print("compact: cannot read arguments; usage: scripts/compact_check.py [--base <ref>]")
        return 2
    if not (ROOT / "install.sh").exists():
        print("compact: skip (not collective-wisdom)")
        return 0
    try:
        rows = sizes(argv[1] if argv else project_config.target_ref())
    except CmdError as e:
        print(f"compact: cannot read the change set: {e}")
        return 2
    for path, before, after in rows:
        print(f"{path} {before} {after} {after - before:+d}")
    before, after = sum(r[1] for r in rows), sum(r[2] for r in rows)
    print(f"total {before} {after} {after - before:+d}")
    net = after - before
    if not rows:
        print("compact: skip (no agent files changed)")
    elif net <= 0:
        print(f"compact: skip (net {net} characters)")
    else:
        print(f"compact: run (+{net} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
