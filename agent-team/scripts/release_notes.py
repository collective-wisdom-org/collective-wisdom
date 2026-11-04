#!/usr/bin/env python3
"""Print every release note, newest first: the docs/superpowers/release-notes/*.md files and the `## Release note` section of every PR merged into main.

Exit 1 when the merged PRs cannot be read (no gh login, offline): the notes on disk are still printed.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

NOTES = root() / "docs" / "superpowers" / "release-notes"
GH = str(Path(__file__).absolute().parent / "gh.sh")
DATED = re.compile(r"# (\d{4}-\d{2}-\d{2}) \S")
PREFIX = re.compile(r"^[a-z]+(\([^)]*\))?!?:\s*")
FOLDER = "docs/superpowers/release-notes/"
# Full ref name: a tag called origin/main would win over the short name.
MAIN = "refs/remotes/origin/main"


def natural(name):
    """Split digits out so cw-13 sorts after cw-9."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]


def section(body):
    """Text of the body's `## Release note` section, up to the next `## ` heading; empty when absent."""
    out = None
    for line in (body or "").splitlines():
        if out is None:
            if re.fullmatch(r"## Release note\s*", line):
                out = []
        elif line.startswith("## "):
            break
        else:
            out.append(line)
    return "\n".join(out or []).strip()


def merged_prs():
    """Merged PRs into main as dicts; raises RuntimeError with the reason when gh fails."""
    cmd = [GH, "pr", "list", "--state", "merged", "--base", "main",
           "--json", "number,title,body,mergedAt", "--limit", "500"]
    try:
        p = subprocess.run(cmd, cwd=root(), capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
        return json.loads(p.stdout)
    except (OSError, ValueError) as e:
        raise RuntimeError(f"{type(e).__name__} {e}")


def utc(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_added(log):
    """{file name: UTC time} from `git log --format=%x00%cI --name-only` output, newest commit first; the newest add of a file wins; a commit that adds several notes is skipped."""
    added = {}
    for commit in log.split("\0")[1:]:
        when, *paths = commit.split("\n")
        names = [p[len(FOLDER):] for p in paths if p.startswith(FOLDER)]
        if len(names) == 1:  # a commit adding several notes is a backfill or a shallow boundary, not their merge
            added.setdefault(names[0], utc(when))
    return added


def file_merge_times():
    """{file name: merge time} for the notes on origin/main; empty when git cannot tell."""
    cmd = ["git", "log", MAIN, "--diff-filter=A", "--format=%x00%cI", "--name-only", "--", FOLDER]
    try:
        p = subprocess.run(cmd, cwd=root(), capture_output=True, text=True, timeout=30)
        return parse_added(p.stdout) if p.returncode == 0 else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def stamp(text, at, headed):
    """Put `Merged <time> UTC.` under the note's heading line, or above its text when it has none."""
    if not at:
        return text
    head, _, rest = text.partition("\n") if headed else ("", "", text)
    return "\n\n".join(filter(None, [head, f"Merged {at:%Y-%m-%d %H:%M} UTC.", rest.strip()]))


def main(argv=()):
    if argv:
        print(__doc__)
        return 0
    notes = []  # (sort key, text)
    merged = file_merge_times()
    for path in NOTES.glob("*.md"):
        text = path.read_text().strip()
        m = DATED.match(text)
        if not m:
            print(f"release-notes: {path.name} has no dated heading", file=sys.stderr)
        at = merged.get(path.name)
        day = (at.date().isoformat() if at else m[1]) if m else ""
        notes.append(((day, at.time().isoformat() if at else "", 0, natural(path.name)), stamp("#" + text if m else text, at, bool(m))))
    failed = None
    try:
        for pr in merged_prs():
            text = section(pr["body"])
            if text:
                at = utc(pr["mergedAt"])
                date = at.date().isoformat()
                title = PREFIX.sub("", pr["title"])
                notes.append(((date, at.time().isoformat(), 1, [pr["number"]]), stamp(f"## {date} {title} (#{pr['number']})\n\n{text}", at, True)))
    except (RuntimeError, KeyError, TypeError, ValueError) as e:
        failed = e
    # Dated notes first, newest merge first (notes without a merge time after the timed ones of their day); undated notes last.
    notes.sort(key=lambda n: (bool(n[0][0]), *n[0]), reverse=True)
    print("# Release notes")
    if not notes:
        print("\nNo release notes yet.")
    for _, text in notes:
        print("\n" + text)
    if failed:
        print(f"release-notes: cannot read merged PRs: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
