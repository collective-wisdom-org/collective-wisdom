#!/usr/bin/env python3
"""The No Hands run: start it, check its limits, drain it, end it. Chief of Staff only, run from the root checkout.

Usage:
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] [--db PATH] start --thread <chiefThreadId>
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] [--db PATH] check
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] drain <reason>
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] end <reason>

A run needs the committed setting (project_config.no_hands_setting: the `No Hands` rows of project.md on origin/<merge target
branch>) and the user's own `no hands` message in the Chief of Staff thread. The run record is the `noHands` key of the state
file, written through cos_state.py's no-hands op: when the run began, the message that began it, the tickets it started (the
start op appends them), the drain reason and how it ended. It is a record, not a rule: active() re-checks the setting, the cost
and the user's message every time, so a record written by anything but `start` approves nothing.

start   Needs the setting on, no active run, the state's chiefThreadId equal to --thread, and the newest user message holding
        the words `no hands` (cos_user_check.py latest; newer than the last run's end, and not `no hands off`). Writes a fresh record.
        Last line: no-hands: started (cap N tickets, $C)  or  no-hands: refused (<why>)
check   Prints one line, read only. The cost is the sum of agent_usage.py --ticket over the run's tickets; a ticket with no
        cost line makes the run stop, since an unmeasured run cannot be held to its cap.
            no-hands: off                          no run, or the run ended
            no-hands: on N/cap $X/$C               N tickets started
            no-hands: drain <reason> N/cap $X/$C   no new starts; approvals stay automatic (ticket-cap is the cap reached)
            no-hands: stop cost-cap $X/$C          the Chief of Staff cancels the children, then `end`
            no-hands: stop <why>                   setting off | start message not verified | cost unknown
drain   Sets the drain reason (the first one stays). Last line: no-hands: drain <reason>
end     Sets endedAt and endReason and prints the run summary: why, how long, each ticket with its state and cost, the total.

Exit codes: 0 ok, 1 refused, or drain and end with no active run, 2 bad arguments or the state file or message store failed.
~/.collective-wisdom/scripts/approval_policy.py and cos_approve_pr.py import active() from here.
"""

import argparse
import contextlib
import io
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import cos_user_check  # noqa: E402
import project_config  # noqa: E402

WORDS, OFF_WORDS = "no hands", "no hands off"
USAGE = str(Path(__file__).absolute().parent / "agent_usage.py")
COST = re.compile(r"cost \$([0-9]+(?:\.[0-9]+)?)")


class Cannot(Exception):
    pass


def ticket_cost(ticket):
    """API-equivalent dollars from `agent_usage.py --ticket`, or None when it prints no cost line."""
    try:
        r = subprocess.run([sys.executable, USAGE, "--ticket", ticket], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    m = COST.match(r.stdout) if r.returncode == 0 else None
    return float(m.group(1)) if m else None


def _load(state_file):
    try:
        return cos_state.load(state_file)
    except SystemExit:
        raise Cannot("read the state file")


def _write(state_file, fields):
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cos_state.apply_file(state_file, [{"op": "no-hands", "set": fields}])
    except SystemExit:
        code = 2
    if code:
        raise Cannot("write the state file: " + (err.getvalue().strip() or "failed"))


def _said(db, thread, words, after=None):
    """(ok, rest): rest is the item id of the user's newest message holding words, or cos_user_check's line when not ok."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cos_user_check.latest(db, thread, words, after)
    except SystemExit:
        return False, "cannot read the message store"
    line = out.getvalue().strip()
    return (True, line.split()[1]) if code == 0 and line.count(" ") >= 1 else (False, line)


def _item_ok(db, thread, item_id):
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cos_user_check.item(db, thread, item_id, WORDS) == 0
    except SystemExit:
        return False


def _is_active(run):
    return isinstance(run, dict) and bool(run.get("startedAt")) and not run.get("endedAt")


def _tickets(run):
    started = run.get("started")
    return [x for x in started if isinstance(x, str)] if isinstance(started, list) else []


def evaluate(setting, state_file, db, cost):
    """(kind, line): kind is off, on, drain or stop; line is what `check` prints. Raises Cannot on an unreadable state file."""
    state = _load(state_file)
    run = state.get("noHands")
    if not _is_active(run):
        return "off", "no-hands: off"
    on, ticket_cap, cost_cap, _ = setting()
    if not on:
        return "stop", "no-hands: stop setting off"
    thread, item = state.get("chiefThreadId"), run.get("itemId")
    if not (thread and item and _item_ok(db, thread, item)):
        return "stop", "no-hands: stop start message not verified"
    tickets, spent = _tickets(run), 0.0
    for t in tickets:
        c = cost(t)
        if c is None:
            return "stop", "no-hands: stop cost unknown"
        spent += c
    money = f"${int(spent)}/${cost_cap}"
    if spent >= cost_cap:
        return "stop", f"no-hands: stop cost-cap {money}"
    progress = f"{len(tickets)}/{ticket_cap} {money}"
    if run.get("drain"):
        return "drain", f"no-hands: drain {run['drain']} {progress}"
    if len(tickets) >= ticket_cap:
        return "drain", f"no-hands: drain ticket-cap {progress}"
    return "on", f"no-hands: on {progress}"


def active(setting=project_config.no_hands_setting, state_file=cos_state.DEFAULT_FILE, db=cos_user_check.DEFAULT_DB, cost=ticket_cost):
    """True only while a run is on or draining: setting on, run started and not ended, cost under the cap, start message still the user's."""
    try:
        return evaluate(setting, state_file, db, cost)[0] in ("on", "drain")
    except Cannot:
        return False


def cmd_start(thread, setting, state_file, db):
    on, ticket_cap, cost_cap, note = setting()
    if not on:
        return 1, f"no-hands: refused (setting is off{'; ' + note if note else ''})"
    state = _load(state_file)
    prior = state.get("noHands")
    if _is_active(prior):
        return 1, "no-hands: refused (a run is active)"
    if not thread or state.get("chiefThreadId") != thread:
        return 1, "no-hands: refused (--thread is not the chiefThreadId in the state file)"
    ended = prior.get("endedAt") if isinstance(prior, dict) else None
    ok, item = _said(db, thread, WORDS, ended if isinstance(ended, str) and cos_user_check.valid_after(ended) else None)
    if not ok:
        return 1, f"no-hands: refused (no new `no hands` from the user: {item})"
    off, off_item = _said(db, thread, OFF_WORDS)
    if off and off_item == item:
        return 1, "no-hands: refused (the newest message is `no hands off`)"
    _write(state_file, {"startedAt": cos_state.now(), "itemId": item, "started": [], "drain": None, "endedAt": None, "endReason": None})
    return 0, f"no-hands: started (cap {ticket_cap} tickets, ${cost_cap})"


def reason_of(words):
    return " ".join(" ".join(words).split())[:100]


def cmd_drain(reason, state_file):
    run = _load(state_file).get("noHands")
    if not _is_active(run):
        return 1, "no-hands: no active run"
    if not run.get("drain"):
        _write(state_file, {"drain": reason})
    return 0, f"no-hands: drain {run.get('drain') or reason}"


def duration(start, end):
    t0 = cos_state.parse(start)
    minutes = int((end - t0).total_seconds() // 60) if t0 else 0
    return f"{minutes // 60}h {minutes % 60:02d}m"


def cmd_end(reason, setting, state_file, cost):
    state = _load(state_file)
    run = state.get("noHands")
    if not _is_active(run):
        return 1, "no-hands: no active run"
    end = datetime.now(timezone.utc)
    rows, spent = [], 0.0
    for t in _tickets(run):
        c = cost(t)
        spent += c or 0.0
        merged = state.get("merged", {}).get(t)
        where = f"merged #{merged.get('pr', '-')}" if isinstance(merged, dict) else (state.get("tickets", {}).get(t) or {}).get("stage", "gone")
        rows.append(f"{t} {where} {'cost unknown' if c is None else f'${int(c)}'}")
    cap = setting()[2]
    _write(state_file, {"endedAt": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "endReason": reason})
    return 0, "\n".join([
        f"no-hands: ended {reason}",
        f"ran: {duration(run['startedAt'], end)}, {len(rows)} tickets started",
        "tickets: " + (", ".join(rows) or "none"),
        f"cost: ${int(spent)}" + (f" of ${cap}" if cap else ""),
    ])


def main(argv, setting=project_config.no_hands_setting, state_file=None, db=None, cost=ticket_cost):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--db", type=Path, default=cos_user_check.DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start").add_argument("--thread", required=True)
    sub.add_parser("check")
    for name in ("drain", "end"):
        sub.add_parser(name).add_argument("reason", nargs="+")
    a = ap.parse_args(argv)
    state_file, db = state_file or a.file, db or a.db
    try:
        if a.cmd == "check":
            code, line = 0, evaluate(setting, state_file, db, cost)[1]
        elif a.cmd == "start":
            code, line = cmd_start(a.thread, setting, state_file, db)
        else:
            reason = reason_of(a.reason)
            if not reason:
                ap.error("reason is empty")
            code, line = cmd_drain(reason, state_file) if a.cmd == "drain" else cmd_end(reason, setting, state_file, cost)
    except Cannot as e:
        code, line = 2, f"no-hands: cannot {e}"
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
