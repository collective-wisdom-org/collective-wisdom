#!/usr/bin/env python3
"""Print every spec, plan and as-built under docs/superpowers as one table sorted by date."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

DOCS = root() / "docs" / "superpowers"
TYPES = (("specs", "Spec"), ("plans", "Plan"), ("as-built", "As-built"))


def title(path):
    for line in path.read_text().splitlines():
        if line.startswith("# "):
            return line[2:].strip().removeprefix("As-built: ")
    return path.name


def main():
    rows = []
    for rank, (folder, kind) in enumerate(TYPES):
        for path in (DOCS / folder).glob("*.md"):
            m = re.match(r"\d{4}-\d{2}-\d{2}", path.name)
            if not m:
                print(f"docs-index: {folder}/{path.name} has no dated name", file=sys.stderr)
            # Undated files sort after every date.
            rows.append((not m, m[0] if m else "", rank, path.name, f"| {m[0] if m else ''} | {kind} | [{title(path)}]({folder}/{path.name}) |"))
    rows.sort()
    print("| Date | Type | Doc |")
    print("|------|------|-----|")
    print("\n".join(r[-1] for r in rows))


if __name__ == "__main__":
    main()
