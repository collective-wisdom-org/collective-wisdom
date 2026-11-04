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


def main(argv=()):
    if argv:
        print(__doc__)
        return 0
    notes = []  # (date, is_pr, order key, text)
    for path in NOTES.glob("*.md"):
        text = path.read_text().strip()
        m = DATED.match(text)
        if not m:
            print(f"release-notes: {path.name} has no dated heading", file=sys.stderr)
        notes.append((m[1] if m else "", 0, natural(path.name), "#" + text if m else text))
    failed = None
    try:
        for pr in merged_prs():
            text = section(pr["body"])
            if text:
                at = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
                date = at.astimezone(timezone.utc).date().isoformat()
                title = PREFIX.sub("", pr["title"])
                notes.append((date, 1, [pr["number"]], f"## {date} {title} (#{pr['number']})\n\n{text}"))
    except (RuntimeError, KeyError, TypeError, ValueError) as e:
        failed = e
    # Dated notes first, newest first; undated notes last.
    notes.sort(key=lambda n: (bool(n[0]), n[0], n[1], n[2]), reverse=True)
    print("# Release notes")
    if not notes:
        print("\nNo release notes yet.")
    for *_, text in notes:
        print("\n" + text)
    if failed:
        print(f"release-notes: cannot read merged PRs: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
