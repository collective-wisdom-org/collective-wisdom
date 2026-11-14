#!/usr/bin/env python3
"""A child's newest assistant message and run status in a few lines, from T3's local store, read-only.

Usage:
    ~/.collective-wisdom/scripts/cos_child_read.py [--db PATH] <PREFIX>-N <childThreadId> [--after POSITION]

Looks at the thread's newest run and, in it, the newest finished assistant message at a position
after --after (a message at or before it is not new). Prints, one fact per line:
    child ABC-5 run=completed updated=2026-11-14T10:02:00Z provider=claudeAgent next=84 item=turn-item:...
    marker BUILD READY
    field specPath=docs/superpowers/specs/x.md specSha=<hex> branch=feat/abc-5-x
    block:
    <the marker block>

marker is BUILD READY (an old SPEC READY counts), MERGE READY, BLOCKED, MERGED or none. The marker is
the last line of the message that starts with one of them, and a block runs from that line to the end
of the message. A run that is not completed prints "marker none", and a completed run with no new
assistant message prints "marker none new=0" (no item=).
field lines: specPath, specSha, branch (from the Spec:, Commit: and Link: lines) for BUILD READY; pr and
headSha (from PR: and Head:) for MERGE READY; pr for MERGED #N. A value that fails its pattern, or a
missing line, prints name=? and the Chief of Staff reads that item in full.
block: follows for BUILD READY, MERGE READY and BLOCKED only. Each line is cut at 200 characters and the
block at 1,500; when anything was cut the last line is "cut <item> at <offset>", the text offset where
the first cut happened, for a full t3_thread_read of that item.
marker none on a completed run prints "tail:" and the message's last 400 characters.

next is the position a t3_thread_read reports for the item (position and nextPosition): the item's
0-based rank among all the thread's items ordered by orchestration_v2_turn_item_positions.ordinal. The
store's ordinals are run number * 1,000,000 + the item's number in the run (1000001, 2000001 ...), so
they are not read positions; the rank is (checked against a real thread: ordinals 1000001, 1000011,
1000022 are positions 0, 10, 21, and 4000008 is 77). With no new item, next is --after (0 without it).
A fallback t3_thread_read afterPosition=<next> returns the items after that item, so it can show a
later message of another role; it never skips one.

--db defaults to ~/.t3/userdata/statev2.sqlite and is opened with mode=ro. Exit 0 with output. Exit 2
and "cos_child_read: schema changed" when the database or a table is not as expected,
"cos_child_read: thread not found" when the thread row is missing.
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_handoff  # noqa: E402
import project_config  # noqa: E402

DEFAULT_DB = Path.home() / ".t3" / "userdata" / "statev2.sqlite"
LINE_CAP, BLOCK_CAP, TAIL_CAP = 200, 1500, 400
MARKER = re.compile(r"^[ \t]*[*`_]*(BUILD READY|SPEC READY|MERGE READY|BLOCKED:|MERGED #(\S*))", re.M)
BRANCH = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]*")
PR = re.compile(r"(?:https://[A-Za-z0-9._/-]+/pull/|#)?([0-9]+)")
NAMES = {"BUILD READY": "BUILD READY", "SPEC READY": "BUILD READY", "MERGE READY": "MERGE READY", "BLOCKED:": "BLOCKED"}
ITEM = (
    "SELECT p.turn_item_id, p.ordinal, json_extract(i.payload_json, '$.text') "
    "FROM orchestration_v2_turn_item_positions p JOIN orchestration_v2_projection_turn_items i "
    "ON i.turn_item_id = p.turn_item_id WHERE p.thread_id = ? AND i.run_id = ? "
    "AND i.type = 'assistant_message' AND json_extract(i.payload_json, '$.streaming') = 0 "
    "ORDER BY p.ordinal DESC LIMIT 1"
)


def fail(msg):
    print(f"cos_child_read: {msg}", file=sys.stderr)
    sys.exit(2)


def fetch(db, thread):
    """(thread row, newest run row, newest assistant item row, its rank) from the store, each None when missing."""
    try:
        con = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
        try:
            one = lambda sql, *args: next(iter(con.execute(sql, args).fetchall()), None)  # noqa: E731
            row = one(
                "SELECT updated_at, COALESCE(provider_instance_id, default_provider) "
                "FROM orchestration_v2_projection_threads WHERE thread_id = ?", thread)
            run = one("SELECT run_id, status FROM orchestration_v2_projection_runs WHERE thread_id = ? ORDER BY ordinal DESC LIMIT 1", thread)
            item = one(ITEM, thread, run[0]) if run else None
            rank = one("SELECT COUNT(*) FROM orchestration_v2_turn_item_positions WHERE thread_id = ? AND ordinal < ?", thread, item[1]) if item else None
            return row, run, item, rank[0] if rank else None
        finally:
            con.close()
    except sqlite3.Error:
        fail("schema changed")


def field(block, label):
    m = re.search(rf"^[ \t]*{label}:[ \t]*(\S+)", block, re.M)
    return m.group(1).strip("`<>*") if m else None


def fields(name, block, arg):
    """The `field` line values for a marker, `?` where a value is missing or fails its pattern."""
    def ok(pattern, value):
        m = pattern.fullmatch(value or "")
        return (m.group(1) if m and m.groups() else value) if m else "?"

    if name == "MERGED":
        return {"pr": ok(re.compile(r"([0-9]+)"), arg)}
    if name == "MERGE READY":
        return {"pr": ok(PR, field(block, "PR")), "headSha": ok(cos_handoff.SHA, field(block, "Head"))}
    if name != "BUILD READY":
        return {}
    spec, link = field(block, "Spec"), field(block, "Link") or ""
    spec = spec if spec and cos_handoff.SPEC_PATH.fullmatch(spec) else None
    m = re.search(r"/blob/(.+)/" + re.escape(spec or "") + "$", link) if spec else None
    return {"specPath": spec or "?", "specSha": ok(cos_handoff.SHA, field(block, "Commit")), "branch": ok(BRANCH, m.group(1) if m else None)}


def cut_block(text, start):
    """The block's lines cut at LINE_CAP each and BLOCK_CAP in all, and the first cut's text offset or None."""
    out, size, first, offset = [], 0, None, start
    for line in text[start:].split("\n"):
        keep = line[: min(LINE_CAP, BLOCK_CAP - size)]
        if len(keep) < len(line) and first is None:
            first = offset + len(keep)
        out.append(keep)
        size += len(keep) + 1
        offset += len(line) + 1
        if size >= BLOCK_CAP:
            if offset < len(text) and first is None:
                first = offset - 1
            break
    return "\n".join(out), first


def read(db, ticket, thread, after):
    row, run, item, pos = fetch(db, thread)
    if not row:
        fail("thread not found")
    status = run[1] if run else "none"
    head = f"child {ticket} run={status} updated={row[0]} provider={row[1] or '?'}"
    floor = -1 if after is None else after
    if not item or pos <= floor:
        print(f"{head} next={max(floor, 0)}")
        print("marker none" + (" new=0" if status == "completed" else ""))
        return
    item, text = item[0], item[2] or ""
    print(f"{head} next={pos} item={item}")
    if status != "completed":
        print("marker none")
        return
    marks = list(MARKER.finditer(text))
    if not marks:
        print("marker none")
        print("tail:")
        print(text.strip()[-TAIL_CAP:])
        return
    m = marks[-1]
    name = NAMES.get(m.group(1), "MERGED" if m.group(1).startswith("MERGED") else "")
    print(f"marker {name}")
    block = text[m.start():]
    vals = fields(name, block, m.group(2))
    if vals:
        print("field " + " ".join(f"{k}={v}" for k, v in vals.items()))
    if name != "MERGED":
        shown, first = cut_block(text, m.start())
        print("block:")
        print(shown)
        if first is not None:
            print(f"cut {item} at {first}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("ticket")
    ap.add_argument("thread")
    ap.add_argument("--after", type=int)
    a = ap.parse_args(argv)
    if not project_config.ticket_re(anchored=True).fullmatch(a.ticket):
        fail("bad ticket")
    read(a.db, a.ticket, a.thread, a.after)
    return 0


if __name__ == "__main__":
    sys.exit(main())
