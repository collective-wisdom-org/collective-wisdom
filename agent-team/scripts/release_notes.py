#!/usr/bin/env python3
"""Print every docs/superpowers/release-notes/*.md note, newest first."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

NOTES = root() / "docs" / "superpowers" / "release-notes"
DATED = re.compile(r"# (\d{4}-\d{2}-\d{2}) \S")


def natural(name):
    """Split digits out so cw-13 sorts after cw-9."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]


def main():
    notes = []
    for path in NOTES.glob("*.md"):
        text = path.read_text().strip()
        m = DATED.match(text)
        if not m:
            print(f"release-notes: {path.name} has no dated heading", file=sys.stderr)
        notes.append((m[1] if m else "", natural(path.name), text))
    # Dated notes first, newest first; undated notes last.
    notes.sort(key=lambda n: (bool(n[0]), n[0], n[1]), reverse=True)
    print("# Release notes")
    if not notes:
        print("\nNo release notes yet.")
    for date, _, text in notes:
        print("\n" + ("#" + text if date else text))


if __name__ == "__main__":
    main()
