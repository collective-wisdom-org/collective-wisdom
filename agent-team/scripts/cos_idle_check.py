#!/usr/bin/env python3
"""Which active children of the Chief of Staff need a full read.

Usage:
    scripts/cos_idle_check.py [--file STATE] [--now ISO] [--skip ABC-N ...] < reads.json
    scripts/cos_idle_check.py --wait ABC-N [--now ISO] < thread_read.json

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

--wait ABC-N asks whether a child whose last run is "completed" is waiting on a
background command. It reads one raw t3_thread_read result (activity view) on
stdin and ignores the state file. The child is waiting when the last run has a
t3_background_wait call with matched IDs and ended at most 45 minutes before --now.
Prints "waiting ABC-N ..." and exits 0 when it is waiting, prints "stalled ABC-N
<reason>" and exits 1 when it is not, and exits 2 when the input can't be judged
(bad input, no run id, or a wait call cut off before its matched list shows).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

ACTIVE = ("spec", "build", "merge")
IDLE_AFTER = timedelta(minutes=45)
DEFAULT_STATE = root() / ".agent-team" / "state.json"


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


WAIT_TOOL = "t3_background_wait"
MATCHED_RE = re.compile(r'\\*"matched\\*":\s*\[\s*\\*"')
UNKNOWN = object()
WAIT_TOOL_RE = re.compile(r'"toolName":\s*"[^"]*' + WAIT_TOOL + '"')


def matched_ids(output):
    """IDs a t3_background_wait call matched, from its parsed output."""
    if not isinstance(output, dict):
        return []
    structured = output.get("structuredContent")
    ids = structured.get("matched") if isinstance(structured, dict) else None
    if not ids:
        try:
            ids = json.loads(output.get("content")).get("matched")
        except (ValueError, TypeError, AttributeError):
            ids = None
    if not isinstance(ids, list):
        return []
    return [i for i in ids if isinstance(i, str) and i]


def wait_calls(items, run_id):
    """Per wait call: its matched ids, None when the text was cut off but shows a
    match (plain or escaped), or UNKNOWN when it was cut off before one."""
    calls = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("runId") != run_id or item.get("type") != "dynamic_tool":
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            call = json.loads(text)
        except ValueError:
            if WAIT_TOOL_RE.search(text):
                calls.append(None if MATCHED_RE.search(text) else UNKNOWN)
            continue
        if not isinstance(call, dict):
            continue
        tool = call.get("toolName")
        if isinstance(tool, str) and tool.endswith(WAIT_TOOL):
            calls.append(matched_ids(call.get("output")))
    return calls


def check_wait(ticket, raw, now):
    """Return (exit code, line): is the child's completed run only a wait?"""
    try:
        read = json.loads(raw)
    except ValueError:
        return 2, "cos_idle_check: bad input"
    runs = read.get("recentRuns") if isinstance(read, dict) else None
    if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
        return 2, "cos_idle_check: no recent run"
    run = runs[0]
    run_id = run.get("runId")
    if not (isinstance(run_id, str) and run_id):
        return 2, "cos_idle_check: no run id"
    if run.get("status") != "completed":
        return 2, "cos_idle_check: last run not completed"
    try:
        ended = parse_ts(run["completedAt"])
    except (KeyError, AttributeError, ValueError, TypeError):
        return 2, "cos_idle_check: no completedAt"
    items = read.get("items")
    calls = wait_calls(items if isinstance(items, list) else [], run_id)
    matched = [c for c in calls if c is None or (c is not UNKNOWN and c)]
    expired = now - ended > IDLE_AFTER
    if not matched:
        if UNKNOWN in calls and not expired:
            return 2, "cos_idle_check: wait call cut off"
        if UNKNOWN not in calls:
            return 1, f"stalled {ticket} " + ("unmatched" if calls else "no-wait")
    if expired:
        minutes = int((now - ended).total_seconds() // 60)
        return 1, f"stalled {ticket} wait-expired {minutes}m"
    ids = list(dict.fromkeys(i for c in matched if c for i in c))
    on = f" on {', '.join(ids)}" if ids else ""
    return 0, f"waiting {ticket}{on}, run ended {hhmm(ended)}"


def main():
    ap = argparse.ArgumentParser(
        description="Which active Chief of Staff children need a full read."
    )
    ap.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_STATE,
    )
    ap.add_argument("--skip", action="append", default=[], metavar="TICKET")
    ap.add_argument("--wait", metavar="TICKET")
    ap.add_argument("--now", type=parse_ts, default=datetime.now(timezone.utc))
    args = ap.parse_args()
    if args.wait:
        code, line = check_wait(args.wait, sys.stdin.read(), args.now)
        print(line)
        raise SystemExit(code)
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
