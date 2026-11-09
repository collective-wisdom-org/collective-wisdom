#!/usr/bin/env python3
"""The No Hands run: start it, check its limits, drain it, end it. Chief of Staff only, run from the root checkout.

Usage:
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] [--db PATH] start --thread <chiefThreadId>
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] [--db PATH] check
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] drain <reason>
    ~/.collective-wisdom/scripts/no_hands.py [--file STATE] end <reason>

A run needs the committed setting (project_config.no_hands_setting: the `No Hands` rows of project.md on origin/<merge target
branch>) and the user's own message `no hands` (the whole message) in the Chief of Staff thread. The run record is the `noHands`
key of the state file, written through cos_state.py's no-hands op, which allows only the moves made here: when the run began, the
message that began it, the tickets it started (the start op appends them), the drain reason and how it ended. It is a record, not
a rule: active() re-checks the setting, the cost and the user's message (the user's newest message that is exactly `no hands`
among those sent no later than startedAt) every time, so a record written by anything but `start` approves nothing. Editing the
state file by hand is out of scope: the record is only as trustworthy as the file. The state file is the root checkout's (the first entry of
`git worktree list`) unless --file is given, so a child in a linked worktree reads the same run.

start   Needs the setting on, no active run, the state's chiefThreadId equal to --thread, and the newest user message holding
        the words `no hands` (cos_user_check.py latest) to be exactly `no hands`, so `no hands off` or `no hands, and delete x` never
        starts a run. That message must also be newer than the last run's end and than the user's latest `stop everything`, and at
        most 10 minutes old. Writes a fresh record.
        Last line: no-hands: started (cap N tickets, $C)  or  no-hands: refused (<why>)
check   Prints one line. It writes only when the result is a stop: it then records endedAt and endReason (the `end` move; the reason
        is the stop's cause as one word, such as cost-cap or stopped-by-user), so a stop is final and the run cannot come back when
        the cause clears. A failed write still prints the stop line. Otherwise it is read only. The cost is the sum of agent_usage.py --ticket over the run's tickets. A ticket with no
        transcripts at all (agent_usage.py: "no transcripts", exit 2) counts as $0 only when the ticket is gone from the state file
        (cancelled early) or is in spec or spec-queued (just started). In any other stage, or merged, the missing transcripts may
        be a Codex or Antigravity child or a moved projects dir, so the cost is unknown; so is a cost that cannot be read for any other
        reason, such as agent_usage.py's `cost unknown` for a Cursor run on a model with no price or an unreadable Cursor store, and an unknown cost makes the run stop, since an unmeasured run cannot be held to its cap.
            no-hands: off                          no run, or the run ended
            no-hands: on N/cap $X/$C               N tickets started
            no-hands: drain <reason> N/cap $X/$C   no new starts; approvals stay automatic (ticket-cap is the cap reached)
            no-hands: stop cost-cap $X/$C          the Chief of Staff cancels the children, then `end`
            no-hands: stop stopped-by-user         the user said `stop everything` after the run began
            no-hands: stop <why>                   setting off | start message not verified
            no-hands: stop cost unknown (<PREFIX>-N)   the first ticket in run order whose cost cannot be read, such as a Cursor run on a model with no price or an unreadable Cursor store
drain   Sets the drain reason (the first one stays). Last line: no-hands: drain <reason>
        drain and end print `no-hands: refused (...)` and exit 2 when a word of the reason is not one the Chief of Staff's plan lines
        may carry (cos_tick.SAFE: letters, digits and . _ : % @ -), since the reason is printed into the tick's report line.
end     Sets endedAt and endReason and prints the run summary: why, how long, each ticket with its state and cost, the total.
        On a run that has ended (by `check` or an earlier `end`) it writes nothing and reposts the summary with the recorded reason, exit 0.

Exit codes: 0 ok, 1 refused, or drain with no active run, or end with neither an active run nor one that ended (`end` on an ended run exits 0
and prints the summary again, so the Chief of Staff calls it once per run), 2 bad arguments or the state file or message store failed.
~/.collective-wisdom/scripts/approval_policy.py and cos_approve_pr.py import active() from here. active(ticket=...) is also true
only when the ticket is on the run's `started` list: approvals under a run cover those tickets only.
"""

import argparse
import contextlib
import io
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import cos_tick  # noqa: E402
import cos_user_check  # noqa: E402
import project_config  # noqa: E402

WORDS = "no hands"
USAGE = str(Path(__file__).absolute().parent / "agent_usage.py")
COST = re.compile(r"cost \$([0-9]+(?:\.[0-9]+)?)")
NO_SESSIONS = "no transcripts for"  # agent_usage.py --ticket stderr (exit 2) when no session ran the ticket
START_WINDOW = timedelta(minutes=10)  # a `no hands` older than this does not start a run
FREE_STAGES = ("gone", "spec", "spec-queued")  # a ticket with no transcripts costs $0 only here


class Cannot(Exception):
    pass


def ticket_cost(ticket, stage="unknown"):
    """API-equivalent dollars from `agent_usage.py --ticket`; None when the cost cannot be read.

    No session ran the ticket: 0.0 when its stage is gone, spec or spec-queued, else None (a child that left no transcript here).
    """
    try:
        r = subprocess.run([sys.executable, USAGE, "--ticket", ticket], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 2 and NO_SESSIONS in r.stderr:
        return 0.0 if stage in FREE_STAGES else None
    m = COST.match(r.stdout) if r.returncode == 0 else None
    return float(m.group(1)) if m else None


def root_state_file():
    """.agent-team/state.json of the root checkout (the first entry of `git worktree list`), also from a linked worktree."""
    try:
        out = subprocess.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True, check=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return cos_state.DEFAULT_FILE
    first = out.strip().split("\n\n")[0].splitlines()
    return Path(first[0].removeprefix("worktree ")) / ".agent-team" / "state.json" if first and first[0].startswith("worktree ") else cos_state.DEFAULT_FILE


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


def _user_rows(db, thread):
    """(message_id, created_at, createdBy, text) of the thread's finished user-role messages; [] when the store cannot be read."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            return cos_user_check.query(db, cos_user_check.SELECT + "AND role = 'user'", (thread,))
    except SystemExit:
        return []


def _stop_time(db, thread):
    """created_at of the user's newest `stop everything` (their own message, not negated), or None."""
    times = [(cos_state.parse(created), created) for _, created, by, text in _user_rows(db, thread)
             if by == "user" and cos_user_check.command_in("stop everything", text or "") == "ok" and getattr(cos_state.parse(created), "tzinfo", None)]
    return max(times, key=lambda x: x[0])[1] if times else None


def _recent(db, thread, item_id, now):
    """True when the message was sent at most START_WINDOW before now (and not after it)."""
    bare = item_id.removeprefix(cos_user_check.PREFIX)
    sent = next((cos_state.parse(created) for mid, created, _, _ in _user_rows(db, thread) if mid == bare), None)
    at = cos_state.parse(now)
    return bool(sent and at and sent.tzinfo and at.tzinfo and timedelta(0) <= at - sent <= START_WINDOW)


def _item_ok(db, thread, item_id, at):
    """True when the item is the user's newest message that is exactly `no hands` (trailing . or ! allowed) sent at or before `at`.

    An older `no hands` cannot be reused for a new record once a newer one exists.
    """
    bare = item_id.removeprefix(cos_user_check.PREFIX)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rows = cos_user_check.query(db, cos_user_check.SELECT + "AND role = 'user'", (thread,))
    except SystemExit:
        return False
    until, sends = cos_state.parse(at), []
    for mid, created, by, text in rows:
        sent = cos_state.parse(created)
        if by == "user" and cos_user_check.norm(text).rstrip(".!") == WORDS and sent is not None and sent.tzinfo is not None:
            sends.append((sent, mid))
    if until is None or until.tzinfo is None:
        return False
    sends = [x for x in sends if x[0] <= until]
    return bool(sends) and max(sends)[1] == bare


def stage_of(state, ticket):
    """merged, the ticket's stage, unknown (a ticket without one), or gone (in neither list)."""
    if isinstance((state.get("merged") or {}).get(ticket), dict):
        return "merged"
    tickets = state.get("tickets", {})
    return ((tickets[ticket] or {}).get("stage") or "unknown") if ticket in tickets else "gone"


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
    if not (thread and item and _item_ok(db, thread, item, run.get("startedAt"))):
        return "stop", "no-hands: stop start message not verified"
    if _said(db, thread, "stop everything", run["startedAt"])[0]:
        return "stop", "no-hands: stop stopped-by-user"
    tickets, spent = _tickets(run), 0.0
    for t in tickets:
        c = cost(t, stage_of(state, t))
        if c is None:
            return "stop", f"no-hands: stop cost unknown ({t})"
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


def active(setting=project_config.no_hands_setting, state_file=None, db=cos_user_check.DEFAULT_DB, cost=ticket_cost, ticket=None):
    """True only while a run is on or draining: setting on, run started and not ended, cost under the cap, start message still the user's.

    With a ticket, also needs the ticket on the run's `started` list: approvals under a run cover only the tickets it started.
    """
    try:
        state_file = state_file or root_state_file()
        if evaluate(setting, state_file, db, cost)[0] not in ("on", "drain"):
            return False
        return ticket is None or ticket in _tickets(_load(state_file).get("noHands"))
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
    started = cos_state.now()
    # The message must be newer than the last run's end and the user's latest `stop everything`, and at most START_WINDOW old.
    floors = [x for x in (ended, _stop_time(db, thread)) if isinstance(x, str) and cos_user_check.valid_after(x)]
    ok, item = _said(db, thread, WORDS, max(floors, key=cos_state.parse) if floors else None)
    if not ok:
        return 1, f"no-hands: refused (no new `no hands` from the user: {item})"
    if not _recent(db, thread, item, started):
        return 1, f"no-hands: refused (the `no hands` message is older than {START_WINDOW.seconds // 60} minutes)"
    if not _item_ok(db, thread, item, started):
        return 1, "no-hands: refused (the newest message with `no hands` is not exactly `no hands`)"
    _write(state_file, {"startedAt": started, "itemId": item, "started": [], "drain": None, "endedAt": None, "endReason": None})
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


def record_stop(line, state_file):
    """Make a stop final: write endedAt and endReason (the end move), so a cause that clears cannot bring the run back.

    Best effort: if the write fails the stop line is still printed, and the Chief of Staff's `end` writes it.
    """
    reason = line.removeprefix("no-hands: stop ").split(" $")[0].split(" (")[0].replace(" ", "-")
    with contextlib.suppress(Cannot):
        _write(state_file, {"endedAt": cos_state.now(), "endReason": reason})


def cmd_end(reason, setting, state_file, cost):
    state = _load(state_file)
    run = state.get("noHands")
    done = isinstance(run, dict) and bool(run.get("endedAt")) and bool(run.get("endReason"))
    if not (_is_active(run) or done):
        return 1, "no-hands: no active run"
    end = cos_state.parse(run["endedAt"]) if done else datetime.now(timezone.utc)
    reason = run["endReason"] if done else reason  # a run that `check` already ended keeps its recorded reason; this only prints the summary
    rows, spent = [], 0.0
    for t in _tickets(run):
        stage = stage_of(state, t)
        c = cost(t, stage)
        spent += c or 0.0
        where = f"merged #{state['merged'][t].get('pr', '-')}" if stage == "merged" else stage
        rows.append(f"{t} {where} {'cost unknown' if c is None else f'${int(c)}'}")
    cap = setting()[2]
    if not done:
        _write(state_file, {"endedAt": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "endReason": reason})
    return 0, "\n".join([
        f"no-hands: ended {reason}",
        f"ran: {duration(run['startedAt'], end)}, {len(rows)} tickets started",
        "tickets: " + (", ".join(rows) or "none"),
        f"cost: ${int(spent)}" + (f" of ${cap}" if cap else ""),
    ])


def main(argv, setting=project_config.no_hands_setting, state_file=None, db=None, cost=ticket_cost):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path)
    ap.add_argument("--db", type=Path, default=cos_user_check.DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start").add_argument("--thread", required=True)
    sub.add_parser("check")
    for name in ("drain", "end"):
        sub.add_parser(name).add_argument("reason", nargs="+")
    a = ap.parse_args(argv)
    state_file, db = state_file or a.file or root_state_file(), db or a.db
    try:
        if a.cmd == "check":
            kind, line = evaluate(setting, state_file, db, cost)
            code = 0
            if kind == "stop":
                record_stop(line, state_file)
        elif a.cmd == "start":
            code, line = cmd_start(a.thread, setting, state_file, db)
        else:
            reason = reason_of(a.reason)
            if not reason:
                ap.error("reason is empty")
            if not all(cos_tick.SAFE.fullmatch(w) for w in reason.split()):
                print("no-hands: refused (a word of the reason has characters a plan line cannot carry; use letters, digits and . _ : % @ -)")
                return 2
            code, line = cmd_drain(reason, state_file) if a.cmd == "drain" else cmd_end(reason, setting, state_file, cost)
    except Cannot as e:
        code, line = 2, f"no-hands: cannot {e}"
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
