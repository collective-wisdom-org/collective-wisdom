#!/usr/bin/env python3
"""Print every docs/superpowers/index/*.md entry as one table sorted by date."""

import re
from pathlib import Path

INDEX = Path(__file__).absolute().parent.parent / "docs" / "superpowers" / "index"


def main():
    rows = [
        line.replace("](../", "](")
        for path in sorted(INDEX.glob("*.md"))
        for line in path.read_text().splitlines()
        if re.match(r"\| \d{4}-\d{2}-\d{2} \|", line)
    ]
    rows.sort(key=lambda r: r[2:12])
    print("| Date | Type | Doc |")
    print("|------|------|-----|")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
