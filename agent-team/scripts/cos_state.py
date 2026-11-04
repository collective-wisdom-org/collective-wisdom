#!/usr/bin/env python3
"""Read and edit the Chief of Staff state file, so nobody prints or rewrites it by hand.

Usage:
    scripts/cos_state.py [--file PATH] show
    scripts/cos_state.py [--file PATH] get GORP-N | --pm
    scripts/cos_state.py [--file PATH] apply < ops.json
    scripts/cos_state.py [--file PATH] prune
    scripts/cos_state.py [--file PATH] init

--file defaults to .agent-team/state.json under the repo root this script lives in.
show prints the working set (a few lines plus one status line per ticket, and the retired
thread ids, oldest first, with "(archived)" on archived ones). get prints
one ticket (or the pm block) as JSON. apply reads a JSON list of operations on stdin and
applies all of them or none: it prints "unchanged", or "saved" and one line per changed
ticket, and writes through a temp file, fsync and os.replace under a flock on state.lock
next to the file. init writes an empty state file if there is none. prune drops old merged and retired entries and unknown top-level keys.

Operations (each {"op": NAME, ...}):
    start     ticket, firstTaskId, childThreadId, status; optional parentThreadId, branch
    stage     ticket, stage, status; optional set (a stage change needs a status line)
    set       ticket, set (ticket fields other than stage)
    merged    ticket, pr
    drop      ticket
    top       set (top-level keys other than tickets, merged, retiredThreads, pm)
    pm        set
    retire    threadId
    archive   threadId, archivedAt (a time, or null to undo)
    unretire  threadId
    prune

Exit codes: 0 ok, 1 an op was rejected ("cos_state: op <i>: <reason>") or no such
ticket, 2 the state file is missing or unreadable.
"""

import argparse
import copy
import fcntl
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402

DEFAULT_FILE = root() / ".agent-team" / "state.json"
TOP = {
    "paused", "chiefThreadId", "chiefSessionId", "takeoverContext", "skillCommit",
    "retiredThreads", "rotation", "rotationHeldUntil", "rateLimitedAt", "wakeTaskId", "wakeAt",
    "merged", "tickets", "pm",
}
TICKET = {
    "stage", "firstTaskId", "childThreadId", "parentThreadId", "status", "branch", "specPath",
    "specSha", "pr", "headSha", "rateLimitResumes", "lastSeenAt", "lastPosition", "resumeStage",
    "pendingRelay", "approvalItemId", "queuedAt", "restarts", "note",
}
STAGES = (
    "spec", "awaiting-spec", "spec-queued", "build-queued", "build",
    "awaiting-merge", "merge-queued", "merge", "blocked",
)
ACTIVE = ("spec", "build", "merge")
PM = {
    "lastCheckAt", "lastDailyAt", "ranked", "rankedAt", "rankedReady", "needsReported", "filled",
    "flaggedDuplicates", "flaggedStale",
}
ID = project_config.ticket_re(anchored=True)
DAY = timedelta(hours=24)


class Reject(Exception):
    pass


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def older_than_day(s):
    t = parse(s)
    return t is not None and datetime.now(timezone.utc) - t > DAY


# ---- operations ----------------------------------------------------------------------


def need(op, *fields, optional=()):
    extra = set(op) - {"op", *fields, *optional}
    if extra:
        raise Reject(f"unknown field {sorted(extra)[0]}")
    for f in fields:
        if op.get(f) in (None, ""):
            raise Reject(f"missing {f}")


def keys_ok(d, allowed, what):
    if not isinstance(d, dict):
        raise Reject("set must be an object")
    for k in d:
        if k not in allowed:
            raise Reject(f"unknown {what} key {k}")


def merge_set(t, sets):
    """t.update(sets), but a dict value for restarts merges into the existing counts."""
    for k, val in sets.items():
        if k == "restarts" and isinstance(val, dict) and isinstance(t.get(k), dict):
            t[k] = {**t[k], **val}
        else:
            t[k] = val


def ticket_of(s, op):
    tid = op.get("ticket")
    if not isinstance(tid, str) or not ID.match(tid):
        raise Reject(f"bad ticket id {tid!r}")
    return tid, s["tickets"].get(tid)


def check(t):
    queued = t["stage"].endswith("-queued")
    if queued and not t.get("pendingRelay"):
        raise Reject(f"stage {t['stage']} needs pendingRelay")
    if not queued and (t.get("pendingRelay") or t.get("queuedAt")):
        raise Reject(f"pendingRelay and queuedAt only belong to a queued stage, not {t['stage']}")


def op_start(s, op):
    need(op, "ticket", "firstTaskId", "childThreadId", "status", optional=("parentThreadId", "branch"))
    tid, t = ticket_of(s, op)
    if t:
        if t.get("childThreadId") != op["childThreadId"]:
            raise Reject(f"{tid} already exists with another childThreadId")
        return
    s["tickets"][tid] = {
        "stage": "spec", "firstTaskId": op["firstTaskId"], "childThreadId": op["childThreadId"],
        "parentThreadId": op.get("parentThreadId"), "status": op["status"],
        "branch": op.get("branch"), "specPath": None, "specSha": None, "pr": None,
        "headSha": None, "rateLimitResumes": 0, "lastSeenAt": now(), "lastPosition": 0,
        "resumeStage": None, "pendingRelay": None, "approvalItemId": None, "queuedAt": None,
        "restarts": {"spec": 0}, "note": "",
    }


STAMPED = ("awaiting-spec", "awaiting-merge", "blocked")  # lastSeenAt here is the approval cut-off


def op_stage(s, op):
    need(op, "ticket", "stage", "status", optional=("set",))
    tid, t = ticket_of(s, op)
    if not t:
        raise Reject(f"no ticket {tid}")
    new, old = op["stage"], t["stage"]
    if new not in STAGES:
        raise Reject(f"unknown stage {new}")
    sets = op.get("set", {})
    keys_ok(sets, TICKET - {"stage"}, "ticket")
    if new in STAMPED and "lastSeenAt" in sets:
        raise Reject(f"lastSeenAt is stamped by the script in {new}")
    if new == "blocked" and old in ACTIVE:
        t["resumeStage"] = old
    elif old == "blocked" and new != "blocked":
        t["resumeStage"] = None
    if not new.endswith("-queued"):
        t.update(pendingRelay=None, approvalItemId=None, queuedAt=None)
    merge_set(t, sets)
    if new != old and new in STAMPED:
        t["lastSeenAt"] = now()
    t.update(stage=new, status=op["status"])
    if new.endswith("-queued") and (new != old or not t.get("queuedAt")):
        t["queuedAt"] = now()
    check(t)


def op_set(s, op):
    need(op, "ticket", "set")
    tid, t = ticket_of(s, op)
    if not t:
        raise Reject(f"no ticket {tid}")
    keys_ok(op["set"], TICKET - {"stage"}, "ticket")
    if t["stage"] in STAMPED and "lastSeenAt" in op["set"]:
        raise Reject(f"lastSeenAt is stamped by the script in {t['stage']}")
    merge_set(t, op["set"])
    check(t)


def op_merged(s, op):
    need(op, "ticket", "pr")
    tid, t = ticket_of(s, op)
    if not t and tid not in s["merged"]:
        raise Reject(f"no ticket {tid}")
    s["tickets"].pop(tid, None)
    if not (isinstance(s["merged"].get(tid), dict) and s["merged"][tid].get("pr") == op["pr"]):
        s["merged"][tid] = {"pr": op["pr"], "at": now()}


def op_drop(s, op):
    need(op, "ticket")
    s["tickets"].pop(ticket_of(s, op)[0], None)


def op_top(s, op):
    need(op, "set")
    keys_ok(op["set"], TOP - {"tickets", "merged", "pm", "retiredThreads"}, "top-level")
    s.update(op["set"])


def op_pm(s, op):
    need(op, "set")
    keys_ok(op["set"], PM, "pm")
    s.setdefault("pm", {}).update(op["set"])


def retired(s, op):
    return next((r for r in s["retiredThreads"] if r.get("threadId") == op.get("threadId")), None)


def op_retire(s, op):
    need(op, "threadId")
    if not retired(s, op):
        s["retiredThreads"].append({"threadId": op["threadId"], "retiredAt": now(), "archivedAt": None})


def op_archive(s, op):
    need(op, "threadId", optional=("archivedAt",))
    if "archivedAt" not in op:
        raise Reject("missing archivedAt")
    entry = retired(s, op)
    if not entry:
        raise Reject(f"no retired thread {op['threadId']}")
    entry["archivedAt"] = op["archivedAt"]


def op_unretire(s, op):
    need(op, "threadId")
    s["retiredThreads"] = [r for r in s["retiredThreads"] if r.get("threadId") != op["threadId"]]


def op_prune(s, op, notes=None):
    need(op)
    for k in [k for k in s if k not in TOP]:
        del s[k]
        if k != "scheduledTaskId" and notes is not None:
            notes.append(f"dropped unknown key {k}")
    for tid, m in list(s["merged"].items()):
        if not isinstance(m, dict):
            m = s["merged"][tid] = {"pr": m, "at": now()}
        elif older_than_day(m.get("at")):
            del s["merged"][tid]
    s["retiredThreads"] = [
        {k: v for k, v in r.items() if k != "scheduledTaskId"}
        for r in s["retiredThreads"]
        if not (r.get("archivedAt") and older_than_day(r["archivedAt"]))
    ]


OPS = {
    "start": op_start, "stage": op_stage, "set": op_set, "merged": op_merged, "drop": op_drop,
    "top": op_top, "pm": op_pm, "retire": op_retire, "archive": op_archive,
    "unretire": op_unretire, "prune": op_prune,
}


def apply_ops(state, ops):
    """Return (new state, change lines, notes). Raises Reject("op <i>: <reason>")."""
    s = copy.deepcopy(state)
    for k, empty in (("tickets", {}), ("merged", {}), ("retiredThreads", [])):
        s.setdefault(k, empty)
    notes = []
    if not isinstance(ops, list):
        raise Reject("op 0: expected a JSON list of operations")
    for i, op in enumerate(ops):
        try:
            if not isinstance(op, dict) or op.get("op") not in OPS:
                raise Reject(f"unknown op {op.get('op') if isinstance(op, dict) else op!r}")
            if op["op"] == "prune":
                op_prune(s, op, notes)
            else:
                OPS[op["op"]](s, op)
        except Reject as e:
            raise Reject(f"op {i}: {e}") from None
    old = state.get("tickets", {})
    lines = [
        f"{tid} {'removed' if tid not in s['tickets'] else s['tickets'][tid]['stage']}"
        for tid in dict.fromkeys([*old, *s["tickets"]])
        if old.get(tid) != s["tickets"].get(tid)
    ]
    return s, lines, notes


# ---- file ----------------------------------------------------------------------------


def load(path):
    try:
        text = path.read_text()
    except FileNotFoundError:
        print("cos_state: no state file", file=sys.stderr)
        sys.exit(2)
    except OSError:
        text = ""
    try:
        state = json.loads(text)
    except ValueError:
        state = None
    if not isinstance(state, dict):
        print("cos_state: unreadable state file", file=sys.stderr)
        sys.exit(2)
    return state


def save(path, state):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        if path.exists():
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def apply_file(path, ops):
    if not path.exists():
        print("cos_state: no state file", file=sys.stderr)
        return 2
    try:
        fd = os.open(path.with_name("state.lock"), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        print("cos_state: cannot lock state file", file=sys.stderr)
        return 2
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load(path)
        try:
            new, lines, notes = apply_ops(state, ops)
        except Reject as e:
            print(f"cos_state: {e}", file=sys.stderr)
            return 1
        if new == state:
            print("unchanged")
        else:
            save(path, new)
            print("\n".join(["saved", *lines]))
        print("\n".join(notes), end="\n" if notes else "")
    return 0


# ---- show ----------------------------------------------------------------------------


def t(s):
    """HH:MM for a time on today's UTC date, the full string otherwise, - for none."""
    if not s:
        return "-"
    d = parse(s)
    return d.astimezone(timezone.utc).strftime("%H:%M") if d and d.date() == datetime.now(timezone.utc).date() else s


def v(x):
    return "-" if x in (None, "") else json.dumps(x, separators=(",", ":")) if isinstance(x, (dict, bool)) else x


def show(s):
    tk = s.get("tickets", {})
    by = lambda *stages: [(i, x) for i, x in tk.items() if x.get("stage") in stages]  # noqa: E731
    out = [
        f"chief={v(s.get('chiefThreadId'))} paused={v(s.get('paused'))} "
        f"rateLimitedAt={t(s.get('rateLimitedAt'))} wakeTaskId={v(s.get('wakeTaskId'))} "
        f"wakeAt={t(s.get('wakeAt'))} rotation={v(s.get('rotation'))} "
        f"rotationHeldUntil={t(s.get('rotationHeldUntil'))} skillCommit={(s.get('skillCommit') or '-')[:7]} "
        f"chiefSessionId={v(s.get('chiefSessionId'))} takeoverContext={v(s.get('takeoverContext'))}",
        "counts " + " ".join(f"{n}={len(by(n))}" for n in ACTIVE)
        + f" active={len(by(*ACTIVE))} awaiting-spec={len(by('awaiting-spec'))}"
        f" awaiting-merge={len(by('awaiting-merge'))} blocked={len(by('blocked'))}",
    ]
    for lane in ("spec", "build", "merge"):
        q = sorted(by(f"{lane}-queued"), key=lambda p: p[1].get("queuedAt") or "")
        out.append(f"queue {lane}: " + (", ".join(f"{i} (since {t(x.get('queuedAt'))})" for i, x in q) or "-"))
    for i, x in tk.items():
        stage = x.get("stage")
        head = f"{i} {stage}"
        if stage in ACTIVE:
            head += f" child={v(x.get('childThreadId'))} pos={v(x.get('lastPosition'))} seen={t(x.get('lastSeenAt'))}"
        elif stage in STAMPED or stage.endswith("-queued"):
            head += f" seen={v(x.get('lastSeenAt'))}"
            if x.get("specPath"):
                head += f" spec={x['specPath']}@{(x.get('specSha') or '')[:7]}"
        elif x.get("specPath"):
            head += f" spec={x['specPath']}@{(x.get('specSha') or '')[:7]}"
        if stage == "blocked":
            head += f" resume={v(x.get('resumeStage'))}"
        if not x.get("parentThreadId"):
            head += " parent=-"
        if x.get("pr"):
            head += f" pr={x['pr']}"
        out += [head, f"  {x.get('status', '')}"]
    merged = s.get("merged") if isinstance(s.get("merged"), dict) else {}
    recent = [
        f"{i} #{m.get('pr', '-')}" for i, m in merged.items()
        if isinstance(m, dict) and not older_than_day(m.get("at"))
    ]
    rt = sorted(
        (r for r in s.get("retiredThreads") or [] if isinstance(r, dict)),
        key=lambda r: str(r.get("retiredAt") or ""),
    )
    pm = s.get("pm") if isinstance(s.get("pm"), dict) else {}
    ranked = " ".join(
        f"{r.get('id')}({r.get('readiness')})" for r in pm.get("ranked") or [] if isinstance(r, dict)
    )
    out += [
        "merged (24h): " + (", ".join(recent) or "-"),
        "retired: " + (" ".join(f"{r.get('threadId')}{'(archived)' if r.get('archivedAt') else ''}" for r in rt) or "-"),
        f"pm: rankedAt={t(pm.get('rankedAt'))} lastDailyAt={t(pm.get('lastDailyAt'))} "
        f"lastCheckAt={t(pm.get('lastCheckAt'))} ranked={ranked or '-'}",
        "unknown keys: " + (" ".join(k for k in s if k not in TOP and k != "scheduledTaskId") or "-"),
    ]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    g = sub.add_parser("get")
    g.add_argument("ticket", nargs="?")
    g.add_argument("--pm", action="store_true")
    sub.add_parser("apply")
    sub.add_parser("prune")
    sub.add_parser("init")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        if a.file.exists():
            print("unchanged")
        else:
            a.file.parent.mkdir(parents=True, exist_ok=True)
            save(a.file, {"paused": False, "tickets": {}, "merged": {}, "pm": {}})
            print("saved")
        return 0

    if a.cmd == "show":
        print(show(load(a.file)))
    elif a.cmd == "get":
        s = load(a.file)
        if a.pm == bool(a.ticket):
            ap.error("give a ticket id or --pm")
        got = s.get("pm", {}) if a.pm else s.get("tickets", {}).get(a.ticket)
        if got is None:
            print(f"cos_state: no ticket {a.ticket}", file=sys.stderr)
            return 1
        print(json.dumps(got, indent=2))
    else:
        try:
            ops = [{"op": "prune"}] if a.cmd == "prune" else json.load(sys.stdin)
        except ValueError:
            print("cos_state: op 0: stdin is not valid JSON", file=sys.stderr)
            return 1
        return apply_file(a.file, ops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
