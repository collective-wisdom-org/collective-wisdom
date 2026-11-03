#!/usr/bin/env python3
"""Which active children of the Chief of Staff need a full read.

Usage:
    scripts/cos_idle_check.py [--file STATE] [--now ISO] [--skip ABC-N ...] < reads.json

Reads .agent-team/state.json (under the repo root unless --file is given) and a
JSON list on stdin with one entry per small child read:
    [{"ticket": "ABC-125", "runStatus": "completed", "updatedAt": "2026-11-02T04:45:10Z"},
     {"ticket": "ABC-130", "error": "thread not found"}]
Prints one line per ticket in stage spec, build or merge, then
"idle-check: <A> active, <F> need a full read". Lines starting "full" need a
full read. Exit 0 when none does, 1 when at least one does, 2 when state or
stdin can't be read (the check did not run). Read-only: nothing is written.
--now is an ISO 8601 time (default: the current UTC time). --skip leaves a ticket
out (the child already read in full this turn).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ACTIVE = ("spec", "build", "merge")
IDLE_AFTER = timedelta(minutes=45)


def parse_ts(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    try:
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except OverflowError:
        raise ValueError(s)


def hhmm(dt):
    return dt.astimezone(timezone.utc).strftime("%H:%M")


def fail(msg):
    print(f"cos_idle_check: {msg}")
    raise SystemExit(2)


def load_state(path):
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        fail("no state file")
    except (OSError, UnicodeDecodeError):
        fail("unreadable state file")
    try:
        state = json.loads(text)
    except ValueError:
        fail("unreadable state file")
    if not isinstance(state, dict) or not isinstance(state.get("tickets"), dict):
        fail("unreadable state file")
    return state


def load_reads(raw):
    try:
        reads = json.loads(raw)
    except ValueError:
        fail("bad input")
    if not isinstance(reads, list) or not all(isinstance(r, dict) for r in reads):
        fail("bad input")
    if not all(isinstance(r.get("ticket"), str) for r in reads):
        fail("bad input")
    return {r["ticket"]: r for r in reads}


def check(ticket, info, read, now):
    """Return (needs a full read, line) for one active ticket."""
    if read is None or read.get("error"):
        return True, f"full {ticket} unread"
    try:
        updated = parse_ts(read["updatedAt"])
    except (KeyError, AttributeError, ValueError):
        return True, f"full {ticket} unread"
    status = read.get("runStatus")
    if not (isinstance(status, str) and re.fullmatch(r"[a-z_-]{1,20}", status)):
        return True, f"full {ticket} unread"
    if status == "running":
        idle = int((now - updated).total_seconds() // 60)
        if now - updated > IDLE_AFTER:
            return True, f"full {ticket} idle {idle}m"
        return False, f"ok {ticket} (running, updated {hhmm(updated)})"
    try:
        seen = parse_ts(info["lastSeenAt"])
    except (KeyError, AttributeError, ValueError):
        seen = None
    if seen is None or updated > seen:
        when = hhmm(seen) if seen else "never"
        return True, (
            f"full {ticket} lost-notice ({status}, updated {hhmm(updated)}, seen {when})"
        )
    return True, f"full {ticket} not-running ({status}, updated {hhmm(updated)})"


def main():
    ap = argparse.ArgumentParser(
        description="Which active Chief of Staff children need a full read."
    )
    ap.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / ".agent-team" / "state.json",
    )
    ap.add_argument("--skip", action="append", default=[], metavar="TICKET")
    ap.add_argument("--now", type=parse_ts, default=datetime.now(timezone.utc))
    args = ap.parse_args()
    state = load_state(args.file)
    reads = load_reads(sys.stdin.read())

    active = sorted(
        t
        for t, info in state["tickets"].items()
        if isinstance(info, dict)
        and info.get("stage") in ACTIVE
        and t not in args.skip
    )
    full = 0
    for ticket in active:
        needs, out = check(ticket, state["tickets"][ticket], reads.get(ticket), args.now)
        full += needs
        print(out)
    print(f"idle-check: {len(active)} active, {full} need a full read")
    raise SystemExit(1 if full else 0)


if __name__ == "__main__":
    main()
