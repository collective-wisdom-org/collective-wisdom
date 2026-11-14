#!/usr/bin/env python3
"""Print the tool calls one Chief of Staff turn needs, in order.

Usage:
    ~/.collective-wisdom/scripts/cos_tick.py --thread ID --trigger start|user|wake|status|notice:THREAD [--after-reads] [--file STATE] [--now ISO]

--thread is this thread's own ID. The turn calls the script twice: without --after-reads for the
look plan (state checks, child reads, idle check, sweep; its last line is `tick --after-reads`),
and with it for the act plan (rate limit, hygiene, slot fill, observe, report, archive, rotation
check), which depends on state alone and can be rerun. While a No Hands run is active (the state's `noHands`
has startedAt and no endedAt) the act plan carries a `run ... no_hands.py check` line before the slot fill. The tick
cannot know its result, so on `drain` or `stop` the model prints no `start-todo` lines and sends nothing beyond what
no-hands.md says. What the state alone shows, the tick does itself: with `noHands.drain` set it drops `start-todo`
(queued sends still go) and reports `filling stopped: No Hands <reason>`. A `send <T> merge` to a ticket with no parentThreadId (no finish
notice will come) is followed by `merge-wait <T>`. The look plan's child reads are `child-read <T> <child> afterPosition=<p>` lines (cos_child_read.py) and its idle check is the one `run … cos_idle_check.py --store [--skip T]` line, with no `idle-read` lines. Every look plan except `start` begins with the provider check: `chief-provider` when the state's `chiefProvider` is missing or names
another thread (read this thread's provider and save it; no mismatch lines then), else one
`harness-mismatch <ticket> child=<provider> chief=<provider>` line per active or queued ticket whose `provider` is set and
differs. A ticket with no `provider` gets no line. Output is numbered lines "N. <text>"; a `stop <reason>` line is the whole plan. Reads .agent-team/state.json (under the repo root unless
--file is given) through cos_state.load; a missing file counts as empty state. Writes nothing.
--now is an ISO 8601 time (default: the current UTC time).
Exit 0 with a plan, 2 with "cos_tick: <what>" when the state file or the arguments can't be used.
"""

import argparse
import io
import json
import re
import sys
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402

LIMITS = {"spec": 2, "build": 2, "merge": 1}
CAP = sum(LIMITS.values())
LANES = tuple(reversed(cos_state.ACTIVE))  # slot fill order: merge, build, spec
FULL_PASS = ("start", "user", "wake")
SCRIPTS = "~/.collective-wisdom/scripts"
AGAIN = "tick --after-reads"
NO_HANDS_CHECK = f"run python3 {SCRIPTS}/no_hands.py check"
ROTATION_CHECK = f"run python3 {SCRIPTS}/cos_rotation_check.py"
STALE_HANDOFF = timedelta(minutes=10)
MAX_WAKE_MS = 6 * 3600 * 1000
SAFE = re.compile(r"[A-Za-z0-9._:%@][A-Za-z0-9._:%@-]*")  # what may be printed into a plan line
DAILY = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
SPEC_USER = "CHIEF OF STAFF: the user approved the spec"
SPEC_AUTO = "CHIEF OF STAFF: auto-approved the spec"
MERGE_USER = "CHIEF OF STAFF: the user approved the merge"
MERGE_AUTO = "CHIEF OF STAFF: auto-approved the merge"
MERGE_CONFLICT = "The user approved the merge at head"


def fail(msg):
    print(f"cos_tick: {msg}")
    raise SystemExit(2)


def safe(value, what):
    """Values from state, a notice or an argument go into plan lines as typed, so a newline or quote must stop the plan."""
    if value not in (None, "") and not (type(value) in (str, int) and SAFE.fullmatch(str(value))):
        fail(f"unsafe {what} in state or arguments")


def check_args(thread, trigger):
    safe(thread, "thread id")
    safe(trigger.partition(":")[2], "notice thread id")


def check_state(state):
    safe(state.get("wakeTaskId"), "wakeTaskId")
    for r in cos_state.dicts(state.get("retiredThreads")):
        if isinstance(r.get("threadId"), str):
            safe(r["threadId"], "retired thread id")
    for tid, t in state["tickets"].items():
        safe(tid, "ticket id")
        if not cos_state.ID.match(tid):
            fail("unsafe ticket id in state or arguments")
        if isinstance(t, dict):
            for field in ("childThreadId", "pr", "headSha", "approvalItemId", "provider"):
                safe(t.get(field), field)
    if isinstance(state.get("chiefProvider"), dict):
        for field in ("threadId", "provider"):
            safe(state["chiefProvider"].get(field), f"chiefProvider {field}")


def when(s):
    """An ISO time as an aware datetime, or None."""
    dt = cos_state.parse(s)
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load(path):
    if not path.exists():
        return {"tickets": {}}
    try:
        with redirect_stderr(io.StringIO()):
            state = cos_state.load(path)
    except SystemExit:
        fail("unreadable state file")
    if not isinstance(state.get("tickets", {}), dict):
        fail("unreadable state file")
    state.setdefault("tickets", {})
    return state


def tickets_in(state, *stages):
    return [(i, t) for i, t in state["tickets"].items() if isinstance(t, dict) and t.get("stage") in stages]


def children(state):
    return [(i, t) for i, t in tickets_in(state, *cos_state.ACTIVE) if t.get("childThreadId")]


def stops(state, thread, trigger, now):
    """The one `stop` line for this thread, or None."""
    rotation = state.get("rotation") if isinstance(state.get("rotation"), dict) else None
    chief = state.get("chiefThreadId")
    to = (rotation or {}).get("to")
    taking_over = trigger == "start" and (to == thread or (not to and (not chief or chief == thread)))
    if not taking_over:
        started = when((rotation or {}).get("startedAt"))
        if rotation and rotation.get("from") == thread and started and now - started > STALE_HANDOFF:
            return "stop failed-handoff"
        retired = {r.get("threadId") for r in cos_state.dicts(state.get("retiredThreads")) if isinstance(r.get("threadId"), str)}
        if (chief and chief != thread) or thread in retired:
            return "stop retired"
    if state.get("paused") and trigger != "status":
        return "stop paused"


def read_line(tid, t):
    pos = t.get("lastPosition")
    pos = pos if isinstance(pos, int) else 0
    return f"child-read {tid} {t['childThreadId']} afterPosition={pos}"


def after_checks(thread):
    return [f"run python3 {SCRIPTS}/cos_sweep.py --thread {thread}", "each full: read", "each sweep line", AGAIN]


def idle_lines(skip=None):
    return [f"run python3 {SCRIPTS}/cos_idle_check.py --store" + (f" --skip {skip}" if skip else "")]


def provider_lines(state, thread):
    """`chief-provider` when this thread's provider isn't recorded, else a `harness-mismatch` line per child on another provider."""
    cp = state.get("chiefProvider")
    chief = cp.get("provider") if isinstance(cp, dict) and cp.get("threadId") == thread else None
    if not chief:
        return ["chief-provider"]
    return [
        f"harness-mismatch {i} child={t['provider']} chief={chief}"
        for i, t in tickets_in(state, *cos_state.ACTIVE, *(f"{s}-queued" for s in cos_state.ACTIVE))
        if t.get("provider") and t["provider"] != chief
    ]


def look(state, thread, trigger):
    if trigger.partition(":")[0] == "start":  # startup.md step 3 reads the provider itself
        return look_plan(state, thread, trigger)
    return provider_lines(state, thread) + look_plan(state, thread, trigger)


def look_plan(state, thread, trigger):
    kind, _, notice = trigger.partition(":")
    kids = children(state)
    if kind == "status":
        return idle_lines() + after_checks(thread)
    out = []
    if kind == "start" and not state["tickets"]:
        out = ["follow startup.md § Setup", "follow startup.md § Start-up clean-up"]
    elif kind == "start":
        return ["follow rotation.md § Thread rotation: Resume mode"]
    elif kind == "wake":
        wake = state.get("wakeTaskId")
        if not wake:
            return ["follow startup.md § Start-up clean-up step 1"]
        out = [f"delete-wake {wake}"]
    if kind != "notice":
        for i, t in kids:
            out += [read_line(i, t), f"pending {t['childThreadId']}"]
        return out + after_checks(thread)
    own = next(((i, t) for i, t in state["tickets"].items() if isinstance(t, dict) and t.get("childThreadId") == notice), None)
    if own is None:
        out.append(f"helper-test {notice}")
    mine = own is not None and own[1].get("stage") in cos_state.ACTIVE
    others = [k for k in kids if not (mine and k[0] == own[0])]
    if mine:
        out += [read_line(*own), f"pending {notice}"]
    if others:
        out += idle_lines(own[0] if mine else None)
    return out + after_checks(thread)


def relay_lines(state, thread, tid, t, lane):
    """What to run before a queued relay goes out, then the send itself."""
    relay = t.get("pendingRelay")
    if not isinstance(relay, str) or not relay:
        return [f"rebuild-relay {tid}"]
    out, spec = [], relay.startswith((SPEC_USER, SPEC_AUTO))
    if relay.startswith((MERGE_USER, MERGE_AUTO)) or MERGE_CONFLICT in relay:
        out.append(f"head-check {tid} pr={t.get('pr') or '-'} head={t.get('headSha') or '-'}")
        if relay.startswith(MERGE_AUTO):
            out.append(f"run python3 {SCRIPTS}/cos_approve_pr.py {tid} --auto")
    elif relay.startswith(SPEC_USER):
        where = re.search(r"^Approval in thread: (\S+)", relay, re.M)
        safe(where and where.group(1), "approval thread id")
        words = re.search(r'approved the spec: "(.*)"\. Continue', relay, re.S)
        out.append(
            f"user-check {tid} {where.group(1) if where else thread} {t.get('approvalItemId') or '-'} "
            f"words={json.dumps(words.group(1) if words else None, ensure_ascii=True)}"
        )
    elif spec:
        out.append(f"run python3 {SCRIPTS}/approval_policy.py auto {tid} spec")
    parent = t.get("parentThreadId")
    if parent and parent != (state.get("chiefThreadId") or thread):
        return out + [f"continuation {tid} {lane}"]
    if spec:
        out.append(f"configure {t.get('childThreadId')} build")
    out.append(f"send {tid} {lane} {json.dumps(relay, ensure_ascii=True)}")
    return out + ([f"merge-wait {tid}"] if lane == "merge" and not parent else [])  # no parent: no finish notice will come


def no_hands_run(state):
    """The active No Hands run record (started, not ended), or None. Same test as no_hands._is_active, without its imports."""
    run = state.get("noHands")
    return run if isinstance(run, dict) and run.get("startedAt") and not run.get("endedAt") else None


def drain_reason(state):
    """The drain reason of an active No Hands run, or None. Printed into the report line, so each word must be safe."""
    run = no_hands_run(state)
    reason = run.get("drain") if run else None
    if not isinstance(reason, str) or not reason.strip():
        return None
    for word in reason.split():
        safe(word, "No Hands drain reason")
    return " ".join(reason.split())


def slot_fill(state, thread, fill=True):
    """(lines, whether a spec slot is left for Todo). Paused and rate limited turns never get here. fill=False sends the queue but starts no Todo."""
    counts = {lane: len(tickets_in(state, lane)) for lane in LANES}
    queues = {
        lane: sorted(
            tickets_in(state, f"{lane}-queued"),
            key=lambda x: (not isinstance(x[1].get("queuedAt"), str), x[1].get("queuedAt") or ""),
        )
        for lane in LANES
    }
    out = []
    while sum(counts.values()) < CAP:
        lane = next((x for x in LANES if counts[x] < LIMITS[x] and queues[x]), None)
        if lane is None:
            break
        tid, t = queues[lane].pop(0)
        out += relay_lines(state, thread, tid, t, lane)
        counts[lane] += 1
    todo = max(0, min(LIMITS["spec"] - counts["spec"], CAP - sum(counts.values()))) if fill else 0
    return out + ["start-todo"] * todo, todo > 0


def hygiene_due(state, now):
    pm = state.get("pm") if isinstance(state.get("pm"), dict) else {}
    last = pm.get("lastDailyAt")
    at = when(last) if isinstance(last, str) and DAILY.fullmatch(last) else None
    return at is None or now - at > cos_state.DAY


def archives(state):
    return [
        f"archive {r['threadId']}"
        for r in cos_state.dicts(state.get("retiredThreads"))
        if isinstance(r.get("threadId"), str) and r["threadId"] and not r.get("archivedAt")
    ]


def act(state, thread, trigger, now):
    kind = trigger.partition(":")[0]
    if kind == "status":
        return archives(state) + [ROTATION_CHECK]
    full, limited = kind in FULL_PASS, bool(state.get("rateLimitedAt"))
    out = []
    if limited:
        task, wake_at = state.get("wakeTaskId"), when(state.get("wakeAt"))
        past = wake_at is not None and wake_at <= now
        if full and task and past:
            return [f"delete-wake {task}", "clear-rate-limit", AGAIN]
        if full and not task and (wake_at is None or past):
            return ["clear-rate-limit", AGAIN]
        if not task and wake_at is not None and not past:
            ms = int((wake_at - now).total_seconds() * 1000) + 120_000
            out.append(f"schedule-wake everyMs={min(max(ms, 60_000), MAX_WAKE_MS)}")
    if full and not limited and (kind == "start" or hygiene_due(state, now)):
        out.append("hygiene")
    if full:
        out.append("prune")
    report = "report"
    if no_hands_run(state):
        out.append(NO_HANDS_CHECK)
    if not limited:
        draining = drain_reason(state)
        lines, free = slot_fill(state, thread, fill=draining is None)
        out += lines
        if not state.get("rotation"):
            out.append("observe")
        report += f" (filling stopped: {f'No Hands {draining}' if draining else 'spec slot free' if free else 'lanes full'})"
    out.append(report)
    return out + archives(state) + [ROTATION_CHECK]


def trigger_arg(s):
    kind, _, thread = s.partition(":")
    if kind in (*FULL_PASS, "status") and not thread or kind == "notice" and thread:
        return s
    raise argparse.ArgumentTypeError(f"bad trigger {s!r}")


def time_arg(s):
    dt = when(s)
    if dt is None:
        raise argparse.ArgumentTypeError(f"bad time {s!r}")
    return dt


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail(message)


def main(argv=None):
    ap = Parser(description="Print the tool calls one Chief of Staff turn needs.")
    ap.add_argument("--thread", required=True)
    ap.add_argument("--trigger", required=True, type=trigger_arg)
    ap.add_argument("--after-reads", action="store_true")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--now", type=time_arg, default=datetime.now(timezone.utc))
    args = ap.parse_args(argv)
    state = load(args.file)
    check_args(args.thread, args.trigger)
    plan = [stops(state, args.thread, args.trigger.partition(":")[0], args.now)]
    if not plan[0]:
        check_state(state)
        plan = act(state, args.thread, args.trigger, args.now) if args.after_reads else look(state, args.thread, args.trigger)
    print("\n".join(f"{n}. {line}" for n, line in enumerate(plan, 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
