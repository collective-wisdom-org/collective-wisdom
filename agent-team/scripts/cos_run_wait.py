#!/usr/bin/env python3
"""Wait for a spec or build child's run to end, even when T3's finish notice is lost (the Chief of Staff's "Run wait").

Usage:
    ~/.collective-wisdom/scripts/cos_run_wait.py <PREFIX>-N [--file STATE] [--db PATH] [--every SECONDS] [--for SECONDS] [--next]

Read only: writes no state, sends nothing. At the start it reads the ticket from .agent-team/state.json (under the repo
root unless --file is given) through cos_state.load, keeps its lane (spec or build) and childThreadId, and reads the child's
newest run from T3's local store (--db, default ~/.t3/userdata/statev2.sqlite, opened mode=ro). Each round (default every
30 seconds, for 110 minutes) it re-reads the ticket, then the child's newest run:
    - the ticket is gone, out of the lane or has another child: done (`left`). A finish notice that did arrive moved it.
    - a run that is running, or the run seen at the start when that was not running then (the send started none yet), is waited on
    - failed, interrupted or cancelled: done
    - completed: a marker after the ticket's lastPosition (found as cos_child_read.py finds it) is done, after one more round
      that re-reads the ticket, so a late finish notice goes first; no marker (a child waiting in t3_background_wait, or a
      stall for the stuck check) keeps waiting
The last line printed and the exit code:
    run-wait: <T> left <lane>                (exit 0)
    run-wait: <T> run <status>               (exit 0) failed, interrupted or cancelled
    run-wait: <T> BUILD READY|MERGE READY|BLOCKED|MERGED  (exit 0)
    run-wait: <T> still working after Nm     (exit 1) the time ran out
    run-wait: cannot <what>                  (exit 2) a bad ticket id, a ticket not in spec or build at the start, no
                                             childThreadId, unreadable state, or a store that is missing or not as expected
--next (without it the output is the last line alone): print `next: <instruction>` after it, from the table NEXT below, for every line it can
print. After a marker, `run <status>` and `still working` the text names the tick to run, with the child's thread id read from state when the
ticket is still there (`<childThreadId>` otherwise).
"""

import argparse
import io
import re
import sys
import time
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_child_read  # noqa: E402
import cos_state  # noqa: E402

LANES = ("spec", "build")
ENDED = ("failed", "interrupted", "cancelled")


class Cannot(Exception):
    pass


def load_ticket(path, tid):
    try:
        with redirect_stderr(io.StringIO()):
            state = cos_state.load(path)
    except SystemExit:
        raise Cannot("read the state file")
    tickets = state.get("tickets")
    if not isinstance(tickets, dict):
        raise Cannot("read the state file")
    return tickets.get(tid)


def lane_child(ticket):
    """(stage, childThreadId) of a ticket in a lane that has a child, else None."""
    if not isinstance(ticket, dict) or ticket.get("stage") not in LANES or not ticket.get("childThreadId"):
        return None
    return ticket["stage"], ticket["childThreadId"]


def read_store(db, thread, after):
    """((newest run id, status) or None, the marker name or None) for the child, from the store."""
    try:
        with redirect_stderr(io.StringIO()):
            row, run, _, _, msgs = cos_child_read.fetch(db, thread, after)
            found = cos_child_read.find_marker(msgs)
    except SystemExit:
        raise Cannot("read the T3 store")
    if not row:
        raise Cannot("find the child thread in the T3 store")
    return run, found and cos_child_read.marker_name(found[2])


def judge(run, start, marker):
    """The end this round shows ('run <status>' or a marker name), or None to keep waiting."""
    if run is None or run[1] == "running" or (run[0] == start[0] and start[1] != "running"):
        return None
    return f"run {run[1]}" if run[1] in ENDED else marker if run[1] == "completed" else None


def wait(tid, read, store, every, limit, clock=time.monotonic, sleep=time.sleep):
    """(last line, exit code). read() gives the ticket; store(thread, after) gives (newest run, marker name)."""
    first = read()
    if not isinstance(first, dict):
        raise Cannot(f"find {tid} in state")
    key = lane_child(first)
    if key is None:
        raise Cannot(f"find {tid} in spec or build with a child thread")
    lane, child = key
    start = store(child, 0)[0] or (None, None)
    began, seen = clock(), None
    while True:
        ticket = read()
        if lane_child(ticket) != key:
            return f"run-wait: {tid} left {lane}", 0
        pos = ticket.get("lastPosition")
        run, marker = store(child, pos if isinstance(pos, int) else 0)
        end = judge(run, start, marker)
        if end and (end.startswith("run ") or end == seen):
            return f"run-wait: {tid} {end}", 0
        seen = end
        if clock() - began + every >= limit:
            return f"run-wait: {tid} still working after {int(limit // 60)}m", 1
        sleep(every)


# --next: what to do when the wait ends, by the line's last words. Two waits on one ticket are harmless: both only read.
TICK = (
    "run the tick with `python3 ~/.collective-wisdom/scripts/cos_tick.py --thread <this thread's id> --trigger 'notice:{child}' --next`: the same "
    "plan as the finish notice that never came (child read, idle check, sweep, slot fill)"
)
NEXT = {
    "marker": "The child ended its run with a marker: " + TICK + ".",
    "run": "The child's run failed, was interrupted or was cancelled: " + TICK + ".",
    "still working": (
        "The time ran out: " + TICK + " once, then start a new run wait (sweep.md § Run wait) if the ticket is still in the same lane with the same child."
    ),
    "left": "Nothing: no tick, no message.",
    "cannot": "One Cleanup line in the next report, `Run wait for <PREFIX>-N: <short title>, <its line>`, and nothing else.",
}


def next_for(line, child):
    """The `next:` text for the wait's last line."""
    if line.startswith("run-wait: cannot"):
        return NEXT["cannot"]
    rest = line.split(" ", 2)[2] if line.count(" ") >= 2 else ""
    key = "left" if rest.startswith("left ") else "still working" if rest.startswith("still working") else "run" if rest.startswith("run ") else "marker"
    return NEXT[key].format(child=child)


def child_of(path, tid):
    """The ticket's childThreadId from state, or `<childThreadId>` when it is gone or unreadable (or holds characters a command line can't carry)."""
    try:
        child = (load_ticket(path, tid) or {}).get("childThreadId")
    except Cannot:
        child = None
    return child if isinstance(child, str) and re.fullmatch(r"[A-Za-z0-9._:%@][A-Za-z0-9._:%@-]*", child) else "<childThreadId>"


def positive(s):
    if not s.isdigit() or int(s) < 1:
        raise argparse.ArgumentTypeError(f"bad number of seconds {s!r}")
    return int(s)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"run-wait: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="Wait for a spec or build child's run to end.")
    ap.add_argument("ticket")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--db", type=Path, default=cos_child_read.DEFAULT_DB)
    ap.add_argument("--every", type=positive, default=30)
    ap.add_argument("--for", dest="limit", type=positive, default=6600)
    ap.add_argument("--next", dest="nxt", action="store_true")
    args = ap.parse_args(argv)
    try:
        if not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        line, code = wait(args.ticket, lambda: load_ticket(args.file, args.ticket), lambda t, a: read_store(args.db, t, a), args.every, args.limit)
    except Cannot as e:
        line, code = f"run-wait: cannot {e}", 2
    print(line)
    if args.nxt:
        print(f"next: {next_for(line, child_of(args.file, args.ticket))}")
    return code


if __name__ == "__main__":
    sys.exit(main())
