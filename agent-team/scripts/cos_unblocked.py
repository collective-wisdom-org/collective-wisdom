#!/usr/bin/env python3
"""Which tickets a merge left with no open blocker, so the Chief of Staff can move them from Backlog to Todo.

Usage:
    ~/.collective-wisdom/scripts/cos_unblocked.py < {"merged": "ABC-M", "tickets": {"ABC-N": <get-ticket JSON>}}

Read only: writes nothing and calls no tracker. `tickets` holds one get-ticket result (fields id, state, labels, relations,
each blocker's state filled in, as readiness.md § Todo start reads them) per ticket the merged ticket blocked. A ticket whose
author the adapter calls untrusted is given as {"untrusted": true}.
Prints, for each ticket in id order, `todo <ID>` when it is in Backlog, not labelled `agent-skip`, not untrusted, and every
blocker other than the merged ticket is closed (cos_todo.is_open). The merged ticket counts as closed whatever state the read
gave it, since the tracker may not have caught up. A blocker is the merged ticket by its id, or by its number alone (GitHub).
Otherwise prints `stay <ID> <why>`: `state <State>`, `agent-skip`, `untrusted`, or `blocked by <ID>[, <ID>...]`.
Ends `unblocked: <C> checked, <T> to Todo`. Exit 0.
Exit 2 with `unblocked: cannot <what>` when stdin is not usable.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_todo  # noqa: E402
import pm_hygiene  # noqa: E402


def ident(blocker):
    """A blocker's id, or `#<number>` when the read gives only a number (GitHub)."""
    if isinstance(blocker, dict):
        return str(blocker["id"]) if blocker.get("id") else f"#{blocker.get('number')}"
    return f"#{blocker}" if type(blocker) is int else str(blocker)


def is_merged(blocker, merged):
    m = re.search(r"(\d+)$", merged)
    return ident(blocker) in (merged, m and f"#{m.group(1)}")


def verdict(got, merged):
    if got.get("untrusted"):
        return "untrusted"
    state = pm_hygiene.state_of(got)
    if state != "Backlog":
        return f"state {state}"
    if "agent-skip" in pm_hygiene.labels_of(got):
        return "agent-skip"
    left = [b for b in cos_todo.blockers(got) if not is_merged(b, merged) and cos_todo.is_open(b)]
    return f"blocked by {', '.join(ident(b) for b in left)}" if left else ""


def lines(text):
    try:
        data = json.loads(text)
        merged, tickets = data["merged"], data["tickets"]
        if not isinstance(merged, str) or not isinstance(tickets, dict) or not all(isinstance(g, dict) for g in tickets.values()):
            raise TypeError
    except (ValueError, KeyError, TypeError):
        raise ValueError("read stdin")
    out = [(tid, verdict(got, merged)) for tid, got in sorted(tickets.items())]
    todo = sum(1 for _, why in out if not why)
    return [f"todo {tid}" if not why else f"stay {tid} {why}" for tid, why in out] + [f"unblocked: {len(out)} checked, {todo} to Todo"]


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"unblocked: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    Parser(description="Which tickets a merge left with no open blocker.").parse_args(argv)
    try:
        print("\n".join(lines(sys.stdin.read())))
    except ValueError as e:
        print(f"unblocked: cannot {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
