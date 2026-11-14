#!/usr/bin/env python3
"""Which active children of the Chief of Staff need a full read.

Usage:
    ~/.collective-wisdom/scripts/cos_idle_check.py [--file STATE] [--now ISO] [--skip ABC-N ...] < reads.json
    ~/.collective-wisdom/scripts/cos_idle_check.py --wait ABC-N [--now ISO] < thread_read.json
    ~/.collective-wisdom/scripts/cos_idle_check.py --store [--db PATH] [--file STATE] [--now ISO] [--skip ABC-N ...]
    ~/.collective-wisdom/scripts/cos_idle_check.py --wait ABC-N --store <childThreadId> [--db PATH] [--now ISO]

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

--store reads the reads from T3's local store (`mode=ro`; --db defaults to
~/.t3/userdata/statev2.sqlite) instead of stdin: each active ticket's `childThreadId` from state, then
the thread's `updated_at`, its newest run's status and its provider. A thread missing from the store
is `full ABC-N unread`. It prints the same lines and exit codes as above, with these additions:
  - each `ok` line ends with the child's link `<t3-thread://v2/<environment id>/<thread id>>`, the id
    from `environment-id` beside the database (the thread id itself when the file is missing);
  - up to 5 `  sub <title> <link>` lines follow an `ok` line, newest first: the threads whose
    lineage parent is that child and whose relationship is `subagent` (not archived or deleted), with
    `[`, `]` and newlines dropped from the title;
  - `provider ABC-N <provider>` follows a ticket's line when the store's provider differs from the
    `provider` saved in state.
Exit 2 and "cos_idle_check: schema changed" when the store or a table is not as expected.
--wait ABC-N --store <childThreadId> does the wait check on the store instead of stdin: the thread's
newest run and its last 10 `dynamic_tool` items go through the same rules.
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

ACTIVE = ("spec", "build", "merge")
IDLE_AFTER = timedelta(minutes=45)
DEFAULT_STATE = root() / ".agent-team" / "state.json"
DEFAULT_DB = Path.home() / ".t3" / "userdata" / "statev2.sqlite"
SUBS = 5


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


def store_rows(db, work):
    """work(con), with the store opened read-only; a store that is not as expected is exit 2."""
    try:
        con = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
        try:
            return work(con)
        finally:
            con.close()
    except sqlite3.Error:
        fail("schema changed")


def environment_id(db):
    try:
        env = (Path(db).parent / "environment-id").read_text().strip()
    except (OSError, UnicodeDecodeError):
        return None
    return env if re.fullmatch(r"[A-Za-z0-9-]+", env) else None


def thread_link(env, thread):
    return f"<t3-thread://v2/{env}/{thread}>" if env else thread


def child_row(con, thread):
    """A read for check(), the store's provider and the newest sub-threads of one child."""
    row = con.execute(
        "SELECT updated_at, COALESCE(provider_instance_id, default_provider), "
        "(SELECT status FROM orchestration_v2_projection_runs r WHERE r.thread_id = t.thread_id ORDER BY r.ordinal DESC LIMIT 1) "
        "FROM orchestration_v2_projection_threads t WHERE thread_id = ?",
        (thread,),
    ).fetchone()
    if row is None:
        return None, None, []
    subs = con.execute(
        "SELECT thread_id, title FROM orchestration_v2_projection_threads "
        "WHERE json_extract(payload_json, '$.lineage.parentThreadId') = ? "
        "AND json_extract(payload_json, '$.lineage.relationshipToParent') = 'subagent' "
        "AND archived_at IS NULL AND deleted_at IS NULL ORDER BY updated_at DESC, thread_id LIMIT ?",
        (thread, SUBS),
    ).fetchall()
    return {"updatedAt": row[0], "runStatus": row[2]}, row[1], subs


def run_store(args):
    state = load_state(args.file)
    active = sorted(
        t
        for t, info in state["tickets"].items()
        if isinstance(info, dict) and info.get("stage") in ACTIVE and t not in args.skip
    )

    def work(con):
        return {
            t: child_row(con, state["tickets"][t].get("childThreadId"))
            if isinstance(state["tickets"][t].get("childThreadId"), str)
            else (None, None, [])
            for t in active
        }

    got = store_rows(args.db, work)
    env, full = environment_id(args.db), 0
    for ticket in active:
        info = state["tickets"][ticket]
        read, provider, subs = got[ticket]
        needs, out = check(ticket, info, read, args.now)
        full += needs
        if needs:
            print(out)
        else:
            print(f"{out} {thread_link(env, info['childThreadId'])}")
            for thread, title in subs:
                title = " ".join(re.sub(r"[\[\]]", "", title or "").split())[:80]
                print(f"  sub {title} {thread_link(env, thread)}")
        if provider and provider != info.get("provider"):
            print(f"provider {ticket} {provider}")
    print(f"idle-check: {len(active)} active, {full} need a full read")
    return 1 if full else 0


def parsed(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def wait_read_from_store(db, thread):
    """The JSON a t3_thread_read activity read gives check_wait(), from the store."""

    def work(con):
        run = con.execute(
            "SELECT run_id, status, completed_at FROM orchestration_v2_projection_runs "
            "WHERE thread_id = ? ORDER BY ordinal DESC LIMIT 1",
            (thread,),
        ).fetchone()
        if run is None:
            return {}
        rows = con.execute(
            "SELECT json_extract(i.payload_json, '$.toolName'), json_extract(i.payload_json, '$.output') "
            "FROM orchestration_v2_projection_turn_items i JOIN orchestration_v2_turn_item_positions p "
            "ON p.turn_item_id = i.turn_item_id WHERE i.thread_id = ? AND i.run_id = ? AND i.type = 'dynamic_tool' "
            "ORDER BY p.ordinal DESC LIMIT 10",
            (thread, run[0]),
        ).fetchall()
        items = [
            {"runId": run[0], "type": "dynamic_tool", "text": json.dumps({"toolName": tool, "output": parsed(out)})}
            for tool, out in rows
        ]
        return {"recentRuns": [{"runId": run[0], "status": run[1], "completedAt": run[2]}], "items": items}

    return json.dumps(store_rows(db, work))


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
    ap.add_argument("--store", nargs="?", const=True, metavar="CHILD_THREAD_ID")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--now", type=parse_ts, default=datetime.now(timezone.utc))
    args = ap.parse_args()
    if args.wait:
        if args.store is True:
            fail("--wait --store needs the child thread id")
        raw = wait_read_from_store(args.db, args.store) if args.store else sys.stdin.read()
        code, line = check_wait(args.wait, raw, args.now)
        print(line)
        raise SystemExit(code)
    if args.store:
        if args.store is not True:
            fail("--store takes a thread id only with --wait")
        raise SystemExit(run_store(args))
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
