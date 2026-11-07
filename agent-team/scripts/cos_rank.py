#!/usr/bin/env python3
"""Check the Backlog ranking child's list and save it as pm.ranked.

Usage:
    ~/.collective-wisdom/scripts/cos_rank.py [--file PATH] --started <ISO Z> [--backlog-count N] [--post] < child_message

--started is the time the ranking began (YYYY-MM-DDTHH:MM:SSZ); it becomes pm.rankedAt.
--backlog-count is the number of Backlog tickets that are neither agent-skip nor an epic,
as the Chief of Staff counted them. Only an empty list reads it: an empty list is saved
only with 0, and a list that is not empty ignores it.
--file defaults to .agent-team/state.json under the repo root this script lives in.
stdin is the child's final message. The last fenced json block is the list (the whole
input when there is no fence): objects with exactly id, title, reason, readiness,
priority and createdAt, in rank order, at most 5 that are not held and at most 5 held.
No id repeats or is a ticket in state.

On success it writes one pm op (ranked, rankedAt, rankedReady, true if any entry is
ready) through cos_state, and prints "GORP-N <readiness>" per entry, or with --post
the Backlog ranking post. On a failed check it writes nothing, prints
"cos_rank: <reason>" and exits 2. That includes an empty list when --backlog-count is 1 or
more, and a --backlog-count that is not a whole number of 0 to 9999. An empty list without
--backlog-count writes nothing and exits 3, which means "count the Backlog and run again".
"""

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402

KEYS = {"id", "title", "reason", "readiness", "priority", "createdAt"}
PRIORITIES = ("Urgent", "High", "Medium", "Low", "No priority")
STARTED = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
FENCE = re.compile(r"```json[^\S\n]*\n(.*?)```", re.S)
BAD_TEXT = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]")
CAP = 5


def line_ok(x, top):
    return isinstance(x, str) and 1 <= len(x) <= top and not BAD_TEXT.search(x)


def validate(text, tickets):
    """Return the ranked list, or raise ValueError("<reason>")."""
    blocks = FENCE.findall(text)
    try:
        ranked = json.loads(blocks[-1] if blocks else text)
    except ValueError:
        raise ValueError("no JSON list in the message") from None
    if not isinstance(ranked, list):
        raise ValueError("not a JSON list")
    seen = set()
    for i, e in enumerate(ranked, 1):
        if not isinstance(e, dict) or set(e) != KEYS:
            raise ValueError(f"entry {i}: needs exactly the keys {', '.join(sorted(KEYS))}")
        eid = e["id"]
        if not isinstance(eid, str) or not cos_state.ID.match(eid):
            raise ValueError(f"entry {i}: bad id")
        if eid in seen or eid in tickets:
            raise ValueError(f"entry {i}: {eid} is repeated or already a team ticket")
        seen.add(eid)
        if not line_ok(e["title"], 200) or not line_ok(e["reason"], 160):
            raise ValueError(f"entry {i}: bad title or reason")
        kind, _, rest = str(e["readiness"]).partition(": ")
        if not (e["readiness"] == "ready" or kind in ("needs", "held") and line_ok(rest, 160)):
            raise ValueError(f"entry {i}: bad readiness")
        if e["priority"] not in PRIORITIES:
            raise ValueError(f"entry {i}: bad priority")
        if cos_state.parse(e["createdAt"]) is None:
            raise ValueError(f"entry {i}: bad createdAt")
    held = sum(e["readiness"].startswith("held: ") for e in ranked)
    if held > CAP or len(ranked) - held > CAP:
        raise ValueError(f"more than {CAP} held or {CAP} not held entries")
    return ranked


def post(ranked):
    out = ["Backlog ranking"]
    for n, e in enumerate(ranked, 1):
        tail = e["readiness"][0].upper() + e["readiness"][1:]
        out.append(f"{n}. {e['id']} {e['title']}. {e['reason']}. {tail}.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--started", required=True)
    ap.add_argument("--backlog-count")
    ap.add_argument("--post", action="store_true")
    a = ap.parse_args(argv)

    started = cos_state.parse(a.started) if STARTED.match(a.started) else None
    if started is None or started > cos_state.parse(cos_state.now()):
        print("cos_rank: bad --started")
        return 2
    if a.backlog_count is not None and not re.fullmatch(r"[0-9]{1,4}", a.backlog_count):
        print("cos_rank: bad --backlog-count")
        return 2
    try:
        ranked = validate(sys.stdin.read(), cos_state.load(a.file).get("tickets", {}))
    except ValueError as e:
        print(f"cos_rank: {e}")
        return 2
    if not ranked:
        if a.backlog_count is None:
            print("cos_rank: empty ranking, count the Backlog and run again with --backlog-count N")
            return 3
        n = int(a.backlog_count)
        if n:
            print(f"cos_rank: empty ranking but the Backlog has at least {n} rankable {'ticket' if n == 1 else 'tickets'}")
            return 2
    op = {"op": "pm", "set": {
        "ranked": ranked, "rankedAt": a.started,
        "rankedReady": any(e["readiness"] == "ready" for e in ranked),
    }}
    with contextlib.redirect_stdout(io.StringIO()):
        code = cos_state.apply_file(a.file, [op])
    if code:
        print("cos_rank: could not save state")
        return 2
    print(post(ranked) if a.post else "\n".join(f"{e['id']} {e['readiness']}" for e in ranked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
