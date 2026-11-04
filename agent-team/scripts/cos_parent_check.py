#!/usr/bin/env python3
"""Which Chief of Staff tickets have a child under an older thread.

Usage:
    scripts/cos_parent_check.py --thread ID [--file PATH]

--thread is this thread's own ID (not read from state, which any local agent can
write). --file overrides .agent-team/state.json under the repo root. Read-only:
nothing is written.

Prints one line per ticket whose parentThreadId is not --thread:
    full <ticket> old-parent <id>      active ticket (spec, build, merge): read the child in full
    full <ticket> unknown-parent       active ticket with no parentThreadId
    idle <ticket> old-parent <id|unknown>   any other stage: no read, but it blocks archiving
Then the archive rule over retiredThreads (oldest first, entries without archivedAt):
    archive <threadId>
    keep <threadId> (<tickets>)        the entry where the walk stopped
and a last line "parent-check: <T> tickets, <O> under an older thread, <F> need a full read".
Exit 0 when no ticket is under an older thread, 1 when one is, 2 when the check did not run.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ACTIVE = {"spec", "build", "merge"}
ID = re.compile(r"[A-Za-z0-9._:-]+")
DEFAULT_STATE = Path(__file__).absolute().parent.parent / ".agent-team" / "state.json"


def check(state, thread, archive=True):
    tickets = state.get("tickets") or {}
    bad = [str(n) for n, t in tickets.items() if not ID.fullmatch(str(n))]
    bad += [str(t.get("parentThreadId")) for t in tickets.values() if t.get("parentThreadId") and not ID.fullmatch(str(t.get("parentThreadId")))]
    bad += [str(r.get("threadId")) for r in state.get("retiredThreads") or [] if r.get("threadId") and not ID.fullmatch(str(r.get("threadId")))]
    if bad:
        raise ValueError("odd id")
    lines = []
    older = full = 0
    for name, t in tickets.items():
        parent = t.get("parentThreadId")
        if parent == thread:
            continue
        older += 1
        if t.get("stage") in ACTIVE:
            full += 1
            lines.append(
                f"full {name} old-parent {parent}" if parent else f"full {name} unknown-parent"
            )
        else:
            lines.append(f"idle {name} old-parent {parent or 'unknown'}")

    unknown = sorted(n for n, t in tickets.items() if not t.get("parentThreadId"))
    retired = [r.get("threadId") for r in state.get("retiredThreads") or []] if archive else []
    archived = {r.get("threadId") for r in state.get("retiredThreads") or [] if r.get("archivedAt")}
    for i, tid in enumerate(retired):
        if not tid:
            lines.append("keep (retired entry without threadId)")
            break
        if tid in archived:
            continue
        if tid == thread:
            lines.append(f"keep {tid} (current thread)")
            break
        holders = sorted(n for n, t in tickets.items() if t.get("parentThreadId") in retired[: i + 1])
        if unknown:
            lines.append(f"keep {tid} (unknown parent: {', '.join(unknown)})")
            break
        if holders:
            lines.append(f"keep {tid} ({', '.join(holders)})")
            break
        lines.append(f"archive {tid}")

    lines.append(
        f"parent-check: {len(tickets)} tickets, {older} under an older thread, {full} need a full read"
    )
    return lines, older


def run(thread, path, archive=True):
    """(lines, older), or None after printing why the check did not run."""
    if not thread.strip():
        print("cos_parent_check: empty --thread")
        return None
    if not path.is_file():
        print("cos_parent_check: no state file")
        return None
    try:
        return check(json.loads(path.read_text()), thread, archive)
    except (OSError, ValueError, AttributeError, TypeError):
        print("cos_parent_check: unreadable state file")
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--thread", required=True)
    ap.add_argument("--file")
    args = ap.parse_args(argv)
    result = run(args.thread, Path(args.file) if args.file else DEFAULT_STATE)
    if result is None:
        return 2
    lines, older = result
    print("\n".join(lines))
    return 1 if older else 0


if __name__ == "__main__":
    sys.exit(main())
