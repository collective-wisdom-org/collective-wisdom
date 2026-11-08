#!/usr/bin/env python3
"""The order the Chief of Staff tries Todo tickets in, and which of them an open blocker rules out.

Usage:
    ~/.collective-wisdom/scripts/cos_todo.py < list-tickets JSON
    ~/.collective-wisdom/scripts/cos_todo.py --relations < {"list": <list-tickets JSON>, "tickets": {"ABC-N": <get-ticket JSON>}}

Reads stdin and nothing else; writes nothing. Two passes, like pm_hygiene.py drift. The list is the one `list-tickets` call
for the team's Todo tickets (fields id, labels, priority, createdAt), as the tracker adapter returns it: a JSON list, or
an object holding an `issues` or `tickets` list. Tickets are tried by priority (Urgent, High, Medium, Low, then none; a
`priority:<name>` label, a name, or Linear's 1 to 4), ties by oldest createdAt, and then in list order.

First pass (the list alone): drops tickets labelled `agent-skip`, prints `get <ID>` for each one left, in order. Make that
`get-ticket` call (fields id, state, labels, relations) once per ticket and run the second pass.
Second pass (--relations): `tickets` holds each get-ticket result. A ticket with an open blocker is dropped. A blocker is
open unless its state is Done, Canceled or Duplicate; a bare id or number with no state counts as open. Blockers are
`relations.blockedBy` (also `blocked_by`, `blockers`) or the `relations` entries whose `type` says blocked by. Prints
`start <ID>` for each ticket left, in order: run the readiness check on each until one starts.
Either pass ends `todo: none` when nothing is left (then project-manager § Backlog pick). Exit 0.
Exit 2 with `todo: cannot <what>` when stdin is not usable, or a get-ticket result is missing in the second pass.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import pm_hygiene  # noqa: E402

PRIORITY = ("urgent", "high", "medium", "low")
BLOCKED_BY = {"blockedby", "blocked_by", "blocked-by", "blockers", "is blocked by", "blocked by"}


class Cannot(Exception):
    pass


def rank(t):
    for label in pm_hygiene.labels_of(t):
        if label.startswith("priority:") and label[9:] in PRIORITY:
            return PRIORITY.index(label[9:])
    p = t.get("priority")
    p = p.get("name", p.get("value")) if isinstance(p, dict) else p
    if type(p) is int and 1 <= p <= 4:
        return p - 1
    return PRIORITY.index(p.lower()) if isinstance(p, str) and p.lower() in PRIORITY else len(PRIORITY)


def created(t):
    dt = cos_state.parse(t.get("createdAt"))
    return (False, dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)) if dt else (True, datetime.min.replace(tzinfo=timezone.utc))


def tried_in_order(tickets):
    """The tickets not labelled agent-skip, best first."""
    kept = [t for t in tickets if "agent-skip" not in pm_hygiene.labels_of(t)]
    return sorted(kept, key=lambda t: (rank(t), created(t)))  # sorted is stable: list order breaks ties


def blockers(got):
    rel = got.get("relations")
    if isinstance(rel, dict):
        return [b for k, v in rel.items() if k.lower() in BLOCKED_BY and isinstance(v, list) for b in v]
    return [r.get("issue") if isinstance(r.get("issue"), dict) else r for r in rel or [] if isinstance(r, dict) and str(r.get("type", "")).lower() in BLOCKED_BY]


def is_open(blocker):
    return not isinstance(blocker, dict) or pm_hygiene.state_of(blocker) not in pm_hygiene.FINISHED


def plan(text, relations):
    try:
        if not relations:
            return [t["id"] for t in tried_in_order(pm_hygiene.ticket_list(text))], "get"
        data = json.loads(text)
        tickets, got = data["list"], data["tickets"]
        ids = [t["id"] for t in tried_in_order(pm_hygiene.ticket_list(json.dumps(tickets)))]
        for tid in ids:
            if not isinstance(got.get(tid), dict):
                raise Cannot(f"find the get-ticket result for {tid}")
        return [tid for tid in ids if not any(is_open(b) for b in blockers(got[tid]))], "start"
    except pm_hygiene.Bad as e:
        raise Cannot(str(e))
    except (ValueError, KeyError, TypeError, AttributeError):
        raise Cannot("read stdin")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"todo: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="The order the Chief of Staff tries Todo tickets in.")
    ap.add_argument("--relations", action="store_true")
    args = ap.parse_args(argv)
    try:
        ids, verb = plan(sys.stdin.read(), args.relations)
    except Cannot as e:
        print(f"todo: cannot {e}")
        return 2
    print("\n".join([f"{verb} {i}" for i in ids] or ["todo: none"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
