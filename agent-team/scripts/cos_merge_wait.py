#!/usr/bin/env python3
"""Wait for a ticket's PR to merge or close, or for the ticket to leave the merge stage (the Chief of Staff's "Merge wait").

Usage:
    ~/.collective-wisdom/scripts/cos_merge_wait.py <PREFIX>-N [--file STATE] [--every SECONDS] [--for SECONDS] [--next]

Read only: writes no state, sends nothing. Each round (default every 30 seconds, for 30 minutes) it reads the ticket from
.agent-team/state.json (under the repo root unless --file is given) through cos_state.load and, while the ticket is in
`merge` with an integer `pr`, runs `~/.collective-wisdom/scripts/gh.sh pr view <pr> --json state` (20 second timeout).
The last line printed and the exit code:
    merge-wait: <T> #PR merged             (exit 0) GitHub says MERGED
    merge-wait: <T> #PR closed             (exit 0) GitHub says CLOSED
    merge-wait: <T> left merge             (exit 0) the ticket is gone from state or no longer in merge
    merge-wait: <T> #PR still open after Nm  (exit 1) the time ran out
    merge-wait: cannot <what>              (exit 2) a bad ticket id, no such ticket at the start, no integer pr,
                                           unreadable state, or 5 GitHub reads in a row that failed or gave bad JSON
The sweep's merged check (cos_merged_check.py --apply) stays the only writer of the `merged` op.
--next (without it the output is the last line alone): print `next: <instruction>` after it, from the table NEXT below, for every line it can
print. After `merged`, `closed` and `still open` the text names the tick to run, with the child's thread id read from state when the ticket is
still there (`<childThreadId>` otherwise).
"""

import argparse
import io
import json
import re
import subprocess
import sys
import time
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_state  # noqa: E402

MAX_FAILS = 5
GH = Path(__file__).absolute().parent / "gh.sh"


class Cannot(Exception):
    pass


def decide(tid, ticket, gh):
    """(line, exit code) when the wait is over, else None. gh is the PR state GitHub gave, or None when not read or unreadable."""
    if not isinstance(ticket, dict) or ticket.get("stage") != "merge":
        return f"merge-wait: {tid} left merge", 0
    pr = ticket.get("pr")
    if type(pr) is not int:
        return "merge-wait: cannot find an integer pr", 2
    if gh in ("MERGED", "CLOSED"):
        return f"merge-wait: {tid} #{pr} {gh.lower()}", 0
    return None


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


def gh_state(raw):
    """The PR state in gh's JSON, or None."""
    try:
        state = json.loads(raw).get("state")
    except (ValueError, AttributeError, TypeError):
        return None
    return state if isinstance(state, str) else None


def run_gh(pr):
    """gh's stdout, or None when it failed or timed out."""
    try:
        p = subprocess.run([str(GH), "pr", "view", str(pr), "--json", "state"], capture_output=True, text=True, timeout=20, cwd=root())
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def wait(tid, read, every, limit, gh=run_gh, clock=time.monotonic, sleep=time.sleep):
    """(last line, exit code). read() gives the ticket; gh(pr) gives gh's JSON text or None."""
    if read() is None:
        raise Cannot(f"find {tid} in state")
    start, fails = clock(), 0
    while True:
        ticket = read()
        done = decide(tid, ticket, None)
        if done:
            return done
        state = gh_state(gh(ticket["pr"]) or "")
        fails = 0 if state else fails + 1
        if fails >= MAX_FAILS:
            raise Cannot(f"read the PR from GitHub {MAX_FAILS} times in a row")
        done = decide(tid, ticket, state)
        if done:
            return done
        if clock() - start + every >= limit:
            return f"merge-wait: {tid} #{ticket['pr']} still open after {int(limit // 60)}m", 1
        sleep(every)


# --next: what to do when the wait ends, by the line's last words. Two waits on one ticket are harmless: both only read.
TICK = (
    "run the tick with `python3 ~/.collective-wisdom/scripts/cos_tick.py --thread <this thread's id> --trigger 'notice:{child}' --next`: the same "
    "plan as the finish notice that never came (child read, idle check, sweep with the merged check, slot fill)"
)
NEXT = {
    "merged": "The PR merged: " + TICK + ".",
    "closed": "The PR was closed: " + TICK + ".",
    "still open": "The time ran out: " + TICK + " once, and start no new wait.",
    "left merge": "Nothing: no tick, no message.",
    "cannot": "One Cleanup line in the next report, `Merge wait for <PREFIX>-N: <short title>, <its line>`, and nothing else.",
}


def next_for(line, child):
    """The `next:` text for the wait's last line."""
    if line.startswith("merge-wait: cannot"):
        return NEXT["cannot"]
    key = "left merge" if line.endswith(" left merge") else "still open" if " still open after " in line else line.rsplit(" ", 1)[1]
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
        print(f"merge-wait: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="Wait for a ticket's PR to merge or close.")
    ap.add_argument("ticket")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--every", type=positive, default=30)
    ap.add_argument("--for", dest="limit", type=positive, default=1800)
    ap.add_argument("--next", dest="nxt", action="store_true")
    args = ap.parse_args(argv)
    try:
        if not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        line, code = wait(args.ticket, lambda: load_ticket(args.file, args.ticket), args.every, args.limit)
    except Cannot as e:
        line, code = f"merge-wait: cannot {e}", 2
    print(line)
    if args.nxt:
        print(f"next: {next_for(line, child_of(args.file, args.ticket))}")
    return code


if __name__ == "__main__":
    sys.exit(main())
