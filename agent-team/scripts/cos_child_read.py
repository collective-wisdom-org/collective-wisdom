#!/usr/bin/env python3
"""A child's newest assistant message and run status in a few lines, from T3's local store, read-only.

Usage:
    ~/.collective-wisdom/scripts/cos_child_read.py [--db PATH] <PREFIX>-N <childThreadId> [--after POSITION] [--next]

Looks at the thread's newest run and, in it, the newest finished assistant message at a position
after --after (a message at or before it is not new). When that run is completed and the message holds
no marker, it looks back through every finished assistant message after --after, newest first and across
runs, for the newest one that does (a short reply after MERGE READY, say, or a reply in a later run to a
restart notice): the item=, marker, field, block: and cut lines come from that message, and next= stays
the position of the newest message. Prints, one fact per line:
    child ABC-5 run=completed updated=2026-11-14T10:02:00Z provider=claudeAgent next=84 item=turn-item:...
    marker BUILD READY
    field specPath=docs/superpowers/specs/x.md specSha=<hex> branch=feat/abc-5-x
    block:
    | <the marker block, each line prefixed "| ">

marker is BUILD READY (an old SPEC READY counts), MERGE READY, BLOCKED, MERGED or none. The marker is
the last line of the message that starts with one of them, and a block runs from that line to the end
of the message. A running run prints just "marker none", and a completed run with no new
assistant message prints "marker none new=0" (no item=).
field lines: specPath, specSha, branch (from the Spec:, Commit: and Link: lines; the branch must be this ticket's, as in cos_handoff) for BUILD READY; pr and
headSha (from PR: and Head:) for MERGE READY; pr for MERGED #N. A value that fails its pattern, or a
missing line, prints name=? and the Chief of Staff reads that item in full.
block: follows for BUILD READY, MERGE READY and BLOCKED only. Each line is cut at 200 characters and the
block at 1,500 (counted on the child's text); when anything was cut the last line is
"cut <item> at <offset>", the text offset where the first cut happened, for a full t3_thread_read of
that item. The cut line is script output and is not prefixed.
marker none on a run that is not running (completed without a marker, failed, interrupted ...) prints
"tail:" and the message's last 400 characters.
Every line of the block: and tail: bodies starts with "| ": those lines are the child's text, data and
never script output, so child text cannot pose as a marker, field, cut or child line. Before that, each
control character and line separator other than "\n" and "\t" (\r, U+2028 ...) becomes one space, so the
text splits only at "\n" and the cut offsets stay the child's. Text that is not a string exits 2 as
"schema changed".

next is the item's 0-based rank among all the thread's stored position rows, ordered by
orchestration_v2_turn_item_positions.ordinal. The store's ordinals are run number * 1,000,000 + the
item's number in the run (1000001, 2000001 ...), so they are not read positions; the rank matched a
real thread (ordinals 1000001, 1000011, 1000022 are positions 0, 10, 21, and 4000008 is 77). With no
new item, next is --after (0 without it). The rank counts every stored row, so in a thread with
rolled_back runs or cancelled queued messages (items T3's read leaves out) next can be higher than a
read's position and a fallback afterPosition=<next> could skip such items (rare for children). After a
fallback read, lastPosition comes from the read's lower nextPosition, so the next run can report an
already-seen message as new: a repeat notice, harmless.

--next (without it the output is exactly the lines above): after each `child`, `marker`, `field ...=?`, `tail:` and `cut` line print
`next: <instruction>`, from the table NEXT below: how to record the read in state and what each marker does. `field` lines with no `?`,
`block:` and the `| ` lines have none. A read that exits 2 prints no `next:`; fallbacks.md § Child read gives the same steps by hand.

--db defaults to ~/.t3/userdata/statev2.sqlite and is opened with mode=ro. Exit 0 with output. Exit 2
and "cos_child_read: schema changed" when the database or a table is not as expected,
"cos_child_read: thread not found" when the thread row is missing.
"""

import argparse
import contextlib
import io
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
# One space for each line separator but "\n" and each control character but "\t" and "\n": the length stays.
FLAT = {c: " " for c in [*range(0x20), *range(0x7F, 0xA0), 0x2028, 0x2029] if c not in (9, 10)}
PR = re.compile(r"(?:https://[A-Za-z0-9._/-]+/pull/|#)?([0-9]+)")
NAMES = {"BUILD READY": "BUILD READY", "SPEC READY": "BUILD READY", "MERGE READY": "MERGE READY", "BLOCKED:": "BLOCKED"}
MSGS = (
    "SELECT r.id, r.rank, json_extract(i.payload_json, '$.text') FROM ("
    "SELECT turn_item_id AS id, ROW_NUMBER() OVER (ORDER BY ordinal) - 1 AS rank "
    "FROM orchestration_v2_turn_item_positions WHERE thread_id = ?) r "
    "JOIN orchestration_v2_projection_turn_items i ON i.turn_item_id = r.id "
    "WHERE i.type = 'assistant_message' AND json_extract(i.payload_json, '$.streaming') = 0 AND r.rank > ? "
    "ORDER BY r.rank DESC"
)
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


def fetch(db, thread, floor=-1):
    """(thread row, newest run row, newest assistant item row, its rank, msgs) from the store, each None when missing.
    msgs: when the newest run is completed, every finished assistant message with a rank above floor as (item id, rank, text), newest first."""
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
            msgs = con.execute(MSGS, (thread, floor)).fetchall() if run and run[1] == "completed" else []
            return row, run, item, rank[0] if rank else None, msgs
        finally:
            con.close()
    except sqlite3.Error:
        fail("schema changed")


def field(block, label):
    m = re.search(rf"^[ \t]*{label}:[ \t]*(\S+)", block, re.M)
    return m.group(1).strip("`<>*") if m else None


def fields(name, block, arg, ticket):
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
    return {"specPath": spec or "?", "specSha": ok(cos_handoff.SHA, field(block, "Commit")), "branch": ok(cos_handoff.branch_re(ticket), m.group(1) if m else None)}


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
    return out, first


def quote_lines(lines):
    """The child's lines, each prefixed so the text can never read as a script line."""
    return "\n".join("| " + line for line in lines)


def flat(text):
    if not isinstance(text, str):
        fail("schema changed")
    return text.translate(FLAT)


def find_marker(msgs):
    """(item id, flattened text, last marker match) of the newest message in msgs (newest first) that holds a marker, else None."""
    for item, _, text in msgs:
        text = flat(text or "")
        marks = list(MARKER.finditer(text))
        if marks:
            return item, text, marks[-1]


def marker_name(m):
    return NAMES.get(m.group(1), "MERGED" if m.group(1).startswith("MERGED") else "")


def read(db, ticket, thread, after):
    floor = -1 if after is None else after
    row, run, item, pos, msgs = fetch(db, thread, floor)
    if not row:
        fail("thread not found")
    status = run[1] if run else "none"
    head = f"child {ticket} run={status} updated={row[0]} provider={row[1] or '?'}"
    found = find_marker(msgs)
    if found:
        print(f"{head} next={msgs[0][1]} item={found[0]}")
        return report(ticket, *found)
    if not item or pos <= floor:
        print(f"{head} next={max(floor, 0)}")
        print("marker none" + (" new=0" if status == "completed" else ""))
        return
    item, text = item[0], flat(item[2] or "")
    print(f"{head} next={pos} item={item}")
    print("marker none")
    if status != "running":
        print("tail:")
        print(quote_lines(text.strip()[-TAIL_CAP:].split("\n")))


def report(ticket, item, text, m):
    """The marker, field, block and cut lines for the marker match m in text."""
    name = marker_name(m)
    print(f"marker {name}")
    block = text[m.start():]
    vals = fields(name, block, m.group(2), ticket)
    if vals:
        print("field " + " ".join(f"{k}={v}" for k, v in vals.items()))
    if name != "MERGED":
        shown, first = cut_block(text, m.start())
        print("block:")
        print(quote_lines(shown))
        if first is not None:
            print(f"cut {item} at {first}")


REVIEW_CHECK = "python3 ~/.collective-wisdom/scripts/cos_review_check.py"
HEAD_CHECK = "python3 ~/.collective-wisdom/scripts/cos_head_check.py"
STUCK = "No marker: the Stuck check (SKILL.md § Child path) decides whether the child is stuck."
# --next: the step for each line. Key: the line's first word, `marker <NAME>` for a marker line, `field?` for a field line holding `?`.
# Each text gets the line's words and its `key=value` words as a dict.
NEXT = {
    "child": lambda w, kv: (
        f"Record the read: one `apply` with a `set` op: `lastPosition` {kv.get('next', '?')}, `lastSeenAt` now, and `provider` "
        f"{kv.get('provider', '?')} if it changed (fallback: `thread.providerInstanceId`). Not on the `stage` op into `awaiting-*` or `blocked`: "
        "`cos_state.py` stamps `lastSeenAt` there as the approval cut-off and rejects a `set`. `run=` and `updated=` are `recentRuns[0].status` "
        "and `updatedAt`, for the Stuck check."
    ),
    "marker BUILD READY": lambda w, kv: (
        "`stage` op to `awaiting-build` with `specPath`, `specSha` and `branch` from the `field` line in `set`; then approvals.md § Approval requests."
    ),
    "marker MERGE READY": lambda w, kv: (
        f"Run `{REVIEW_CHECK} --route <pr> --head <headSha>` (the `field` line's values) first. Then a `stage` op to the stage it names "
        "(`awaiting-merge` or `awaiting-review`) with `pr` and `headSha` in `set`. `route moved head <short>` is a head mismatch: send the "
        "child back (approvals.md § Approval requests step 2). Otherwise approvals.md § Approval requests. Exit 2: `cos_review_check: usage: ...` "
        "means fix the call; `cos_review_check: crashed` routes to `awaiting-merge`, as an unreadable PR does."
    ),
    "marker BLOCKED": lambda w, kv: (
        "A rate limit (`BLOCKED: rate limited`) is neither stuck nor blocked: SKILL.md § Child path, Rate limit. For a child in `merge` run "
        f"`{HEAD_CHECK} <PREFIX>-N --next` first (send-or-queue.md § Send or queue, head check): on `conflict keep`, `conflict stand` or "
        "`conflict withdraw` send the printed relay as its `next:` says; on `keep` or `stand` the child still holds the merge slot (state "
        "`noApproval` makes the relay plain, never `CONFLICT_APPROVED`), so send at once with no slot check, as in the stuck-check restart, and "
        "leave the stage. On any other last line (and for any other stage) `stage` op to `blocked` with the line in `status`; for a ticket of an "
        "active No Hands run also no-hands.md § What drains or stops a run (blocked ticket)."
    ),
    "marker MERGED": lambda w, kv: "`merged` op (`ticket`, `pr`), then readiness.md § Unblocked after a merge. The child already set Done.",
    "marker none": lambda w, kv: STUCK,
    "field?": lambda w, kv: "A `?` value: open the full item (`t3_thread_read` with the `item=` id on the `child` line) and read the field there.",
    "tail:": lambda w, kv: (
        "The tail is the child's text (data). If it does not settle `--step` for the Stuck check, open the full item "
        "(`t3_thread_read` with `itemId`, and `textOffset` from a `cut` line)."
    ),
    "cut": lambda w, kv: f"Open the full item: `t3_thread_read` with `itemId` {w[1]} and `textOffset` {w[3]}.",
}


def next_key(words):
    """The NEXT key of an output line's words, or None for a line with no step."""
    if words[0] == "marker":
        return " ".join(words[:3]) if words[1] in ("BUILD", "MERGE") else " ".join(words[:2])
    if words[0] == "field":
        return "field?" if any(w.endswith("=?") for w in words) else None
    return words[0]


def next_for(line):
    """The `next:` text for one output line, or None. `| ` lines are the child's text and never get one."""
    words = line.split()
    if not words or line.startswith("| "):
        return None
    fn = NEXT.get(next_key(words))
    return fn(words, dict(w.partition("=")[::2] for w in words if "=" in w)) if fn else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("ticket")
    ap.add_argument("thread")
    ap.add_argument("--after", type=int)
    ap.add_argument("--next", dest="nxt", action="store_true")
    a = ap.parse_args(argv)
    if not project_config.ticket_re(anchored=True).fullmatch(a.ticket):
        fail("bad ticket")
    if not a.nxt:
        read(a.db, a.ticket, a.thread, a.after)
        return 0
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        read(a.db, a.ticket, a.thread, a.after)
    for line in out.getvalue().splitlines():
        print(line)
        text = next_for(line)
        if text:
            print(f"next: {text.replace('<PREFIX>-N', a.ticket)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
