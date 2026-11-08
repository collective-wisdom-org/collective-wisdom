#!/usr/bin/env python3
"""The Chief of Staff's stuck check for one child, and the restart message.

Usage:
    ~/.collective-wisdom/scripts/cos_restart.py <PREFIX>-N --run completed|failed|interrupted|running --updated-at ISO
        [--marker] [--wait 0|1|2|2twice] [--step TEXT] [--missing TEXT] [--spec PATH] [--file STATE] [--thread ID] [--now ISO]

Read only: sends, cancels and writes nothing. The model reads the child (t3_thread_read, the wait check) and passes what
it found: --run is recentRuns[0].status, --updated-at the thread's updatedAt, --marker that the last assistant message has
a marker, --wait the exit code of `cos_idle_check.py --wait` (0 waiting, 1 stalled, 2 unreadable; `2twice` when a second
read is unreadable too), --step the last step the child finished (one line), --missing the next step (one line) and --spec
the spec path when the child's last message gave one. Reads the ticket's stage, restarts, parentThreadId, pr and the
chiefThreadId from .agent-team/state.json (under the repo root unless --file is given; --thread is this thread's ID, used as
the Chief of Staff thread when state has no chiefThreadId, as in cos_route.py), the review mode from project_config,
and, in `build` or `merge` with a PR, the PR facts by calling cos_brief.cmd_pr (what `cos_brief.py pr <N>` prints).

A ticket in spec, build or merge is stuck when the run failed or was interrupted; when it completed with no marker and the
wait check did not say waiting (0); or when it is running and updatedAt is more than 45 minutes before --now. --wait is
needed only for a completed run with no marker; `2` (read once more, then pass `2twice` or the new result) exits 2.
A ticket in any other stage is skipped. Prints, then a last line, exit 0 unless noted:
    cancel: task_cancel(firstTaskId) first        a stuck running child, before anything below
    --- the restart message, between two --- lines ---
    set: <JSON set op>                            restarts[stage] = 1
    moving: <line>                                copy under Moving
    cleanup: <line>                               copy under Cleanup (an unreadable wait check)
    restart: not-stuck                            no restart, no report line
    restart: send <lane> [cancel]                 t3_thread_send the message, apply the set op; `cancel` means
                                                  task_cancel(firstTaskId) first
    restart: continuation <lane>                  the same text as a relay for continuation.md § Continuation child,
                                                  in place of the send (parentThreadId is known and is not the Chief of Staff thread)
    restart: blocked <why>                        stage op to `blocked` with <why> in `status`, comment it, report it
                                                  (after `stalled`, quote the wait check's own line too)
    restart: unreadable                           an unreadable wait check on a ticket already restarted: not blocked; add the cleanup line
    restart: cannot <what>                        (exit 2) bad arguments, unreadable state, or a PR that cannot be read
A restart is sent when restarts[stage] is 0; otherwise the ticket is blocked (never on an unreadable wait check).
"""

import argparse
import io
import json
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_brief  # noqa: E402
import cos_state  # noqa: E402
import project_config  # noqa: E402

IDLE_AFTER = timedelta(minutes=45)
WAITS = ("0", "1", "2", "2twice")
REVIEW = re.compile(r"(not posted|pass (?:\d+|\?) (?:PASS|CHANGES NEEDED|\(no verdict\)))(?: https?://\S*)?(?: \((?:\d\d:\d\d)?\))?")


class Cannot(Exception):
    pass


def load(path):
    try:
        with redirect_stderr(io.StringIO()):
            state = cos_state.load(path)
    except SystemExit:
        raise Cannot("read the state file")
    if not isinstance(state.get("tickets"), dict):
        raise Cannot("read the state file")
    return state


def when(s):
    dt = cos_state.parse(s)
    if dt is None:
        raise Cannot(f"read the time {s!r}")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def one_line(s):
    return " ".join(s.split()).rstrip(".")


def pr_line(n):
    """`PR #N, head <sha>. On the PR: ...` from what `cos_brief.py pr N` prints."""
    out = io.StringIO()
    try:
        mode = project_config.review_mode()
        with redirect_stdout(out):
            cos_brief.cmd_pr(argparse.Namespace(number=n, head=None))
    except (SystemExit, Exception):
        raise Cannot(f"read PR #{n}")
    facts = dict(x.split(": ", 1) for x in out.getvalue().splitlines() if ": " in x)
    head = re.match(r"[0-9a-f]+", facts.get("head", ""))
    if not head:
        raise Cannot(f"read PR #{n}")
    sha = head.group()
    if mode == "ci":
        ci = re.search(r"\d+ fixed, \d+ answered and resolved, \d+ unresolved$", facts.get("ci-review", ""))
        green = facts.get("ci", "").startswith("green")
        if not ci:
            raise Cannot(f"read PR #{n}")
        on_pr = f"CI {'green' if green else 'not green'} at {sha}, CI review {ci.group()}"
    else:
        found = {k: REVIEW.fullmatch(facts.get(k, "")) for k in ("code review", "security review")}
        if not all(found.values()):
            raise Cannot(f"read PR #{n}")
        on_pr = ", ".join(f"{k} {m.group(1).strip()}" for k, m in found.items())
    return f"PR #{n}, head {sha}. On the PR: {on_pr}."


def message(stage, pr, run, minutes, step, missing, spec, continuation):
    ended = "went quiet" if run == "running" else "ended"
    who = "the previous child's last run" if continuation else "Your last run"
    lines = [f"CHIEF OF STAFF: restart. {who} {ended} {minutes} min ago without a marker, after: {step}."]
    if stage == "spec":
        lines += [f"Spec: {spec}."] if spec else []
    elif pr:
        lines.append(pr_line(pr))
    return "\n".join(lines + [f"Missing: {missing}.", "Keep the run going until you end with a marker."])


def judge(state, tid, args, now):
    """(lines, last line)."""
    ticket = state["tickets"].get(tid)
    if not isinstance(ticket, dict):
        raise Cannot(f"find {tid} in state")
    stage = ticket.get("stage")
    if stage not in cos_state.ACTIVE:
        return [], "restart: not-stuck"
    minutes = max(0, int((now - when(args.updated_at)).total_seconds() // 60))
    run, wait = args.run, args.wait
    if run == "completed" and not args.marker:
        if wait is None:
            raise Cannot("judge a completed run with no marker without --wait")
        if wait == "2":
            raise Cannot("read the wait check; read once more and pass 2twice or the new result")
    stuck = {
        "failed": True, "interrupted": True, "running": now - when(args.updated_at) > IDLE_AFTER,
        "completed": not args.marker and wait != "0",
    }[run]
    if not stuck:
        return [], "restart: not-stuck"
    cancel = ["cancel: task_cancel(firstTaskId) first"] if run == "running" else []
    unreadable = wait == "2twice" and run == "completed" and not args.marker
    restarts = ticket.get("restarts") if isinstance(ticket.get("restarts"), dict) else {}
    cleanup = [f"cleanup: {tid} wait check unreadable; not blocked"] if unreadable else []
    if restarts.get(stage):
        if unreadable:
            return cleanup, "restart: unreadable"
        why = "the wait check says stalled" if run == "completed" else f"last run {run}"
        return cancel, f"restart: blocked restarted already; {why}"
    if not (args.step and args.missing):
        raise Cannot("restart without --step and --missing")
    parent, chief = ticket.get("parentThreadId"), state.get("chiefThreadId") or args.thread
    continuation = bool(parent and parent != chief)
    pr = ticket.get("pr") if stage in ("build", "merge") and ticket.get("pr") else None
    if pr is not None and not (isinstance(pr, int) or str(pr).isdigit()):
        raise Cannot(f"read the pr in state for {tid}")
    step = one_line(args.step)
    text = message(stage, int(pr) if pr else None, run, minutes, step, one_line(args.missing), args.spec and one_line(args.spec), continuation)
    lines = [*cancel, "---", text, "---", f"set: {json.dumps({'op': 'set', 'ticket': tid, 'set': {'restarts': {stage: 1}}})}",
             f"moving: {tid} restarted: stalled after {step}, {minutes} min idle", *cleanup]
    return lines, f"restart: {'continuation' if continuation else 'send'} {stage}" + (" cancel" if cancel and not continuation else "")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"restart: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="The stuck check and restart message for one child.")
    ap.add_argument("ticket")
    ap.add_argument("--run", required=True, choices=("completed", "failed", "interrupted", "running"))
    ap.add_argument("--updated-at", required=True)
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--wait", choices=WAITS)
    ap.add_argument("--step")
    ap.add_argument("--missing")
    ap.add_argument("--spec")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--thread")
    ap.add_argument("--now")
    args = ap.parse_args(argv)
    try:
        if not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        lines, last = judge(load(args.file), args.ticket, args, when(args.now) if args.now else datetime.now(timezone.utc))
    except Cannot as e:
        print(f"restart: cannot {e}")
        return 2
    print("\n".join([*lines, last]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
