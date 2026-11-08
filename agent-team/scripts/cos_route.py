#!/usr/bin/env python3
"""Where a relay goes: send now, queue, or start a continuation child (the Chief of Staff's "Send or queue").

Usage:
    ~/.collective-wisdom/scripts/cos_route.py <PREFIX>-N <caller> [--file STATE] [--thread ID]

Read only: sends nothing and writes no state. Reads the ticket from .agent-team/state.json (under the repo root unless
--file is given) through cos_state.load, the lane limits from cos_tick.LIMITS and CAP, and, for the conflict callers,
`Review after conflict resolution` through project_config.review_after_conflict() (an unreadable setting counts as `on`).
--thread is this thread's ID, used as the Chief of Staff thread when state has no chiefThreadId (as cos_tick does).

The caller and the ticket's stage give the lane:

    caller             from                                        lane
    approve-spec       awaiting-build                              build  (run the Models switch, t3_thread_configure, just before the send)
    approve-merge      awaiting-merge                              merge
    changes            awaiting-build                              spec
    changes            awaiting-review, awaiting-merge             build
    reviewer-changes   awaiting-review                             build
    head-moved         awaiting-review, awaiting-merge,            build
                       merge-queued
    conflict-keep      awaiting-merge, merge-queued                merge  (only with the setting `off`)
    conflict-stand     awaiting-review, awaiting-merge             merge  (only with the setting `off`; the stage op sets noApproval)
    conflict-withdraw  awaiting-review, awaiting-merge,            build
                       merge-queued, merge
    answer, resume,    blocked                                     the lane of the ticket's resumeStage
    rate-limit

The ticket's own slot does not count against it. The relay is sent when the lane is under its limit, the overall count
is under the cap and no ticket waits ahead of it in the lane's queue (any queued ticket, or, for a ticket already in that
queue, one with an older queuedAt; a missing queuedAt sorts last, as in cos_tick); otherwise it is queued. A send to a ticket
whose parentThreadId is known and is not the Chief of Staff thread is a continuation instead (continuation.md).
Prints lines the caller acts on, then a last line, exit 0 unless noted:
    stage: <JSON stage op>                  to apply (a send: the lane's active stage; a queue: <lane>-queued, to which
                                            the caller adds pendingRelay and, for a user spec approval, approvalItemId)
    set: <JSON>                             a continuation has no stage op: add these keys to the lane's stage op
    moving: <line>                          copy under Moving (a send to a ticket with no known parent thread)
    fallback: <line>                        a continuation that falls back to sending to the old child adds this
    route: send <lane>                      send with t3_thread_send, then apply the stage op
    route: queue <lane>                     do not send; apply the stage op
    route: continuation <lane>              continuation.md § Continuation child, in place of the send
    route: no <why>                         (exit 1) the caller does not apply from this stage: do not send
    route: cannot <what>                    (exit 2) state unreadable or a bad argument
"""

import argparse
import io
import json
import sys
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import cos_tick  # noqa: E402
import project_config  # noqa: E402

ROUTES = {  # caller -> {from stage: lane}
    "approve-spec": {"awaiting-build": "build"},
    "approve-merge": {"awaiting-merge": "merge"},
    "changes": {"awaiting-build": "spec", "awaiting-review": "build", "awaiting-merge": "build"},
    "reviewer-changes": {"awaiting-review": "build"},
    "head-moved": {s: "build" for s in ("awaiting-review", "awaiting-merge", "merge-queued")},
    "conflict-keep": {"awaiting-merge": "merge", "merge-queued": "merge"},
    "conflict-stand": {"awaiting-review": "merge", "awaiting-merge": "merge"},
    "conflict-withdraw": {s: "build" for s in ("awaiting-review", "awaiting-merge", "merge-queued", "merge")},
    "answer": {"blocked": "resume"},
    "resume": {"blocked": "resume"},
    "rate-limit": {"blocked": "resume"},
}
MAY_NOT_HEAR = "{ticket}: I may not hear when this run ends; say status to check."


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


def lane_for(caller, ticket, setting):
    """The lane, or None when the caller does not apply from the ticket's stage."""
    lane = ROUTES[caller].get(ticket.get("stage"))
    if lane == "resume":
        lane = ticket.get("resumeStage")
        return lane if lane in cos_state.ACTIVE else None
    if caller in ("conflict-keep", "conflict-stand") and lane and setting() == "on":
        return None
    return lane


def queue_key(t):
    """cos_tick's queue order: oldest queuedAt first, a missing one last."""
    return (not isinstance(t.get("queuedAt"), str), t.get("queuedAt") or "")


def route(state, tid, caller, thread, setting):
    """(lines, last line, exit code)."""
    ticket = state["tickets"].get(tid)
    if not isinstance(ticket, dict):
        raise Cannot(f"find {tid} in state")
    lane = lane_for(caller, ticket, setting)
    if lane is None:
        stage = ticket.get("stage")
        return [], f"route: no {caller} does not apply from {stage if stage in cos_state.STAGES else 'an unknown stage'}", 1
    others = [(i, t) for i, t in state["tickets"].items() if i != tid and isinstance(t, dict)]
    count = lambda *stages: sum(t.get("stage") in stages for _, t in others)  # noqa: E731
    waiting = count(f"{lane}-queued")
    if ticket.get("stage") == f"{lane}-queued":  # in the queue itself, only a ticket queued before it waits ahead
        waiting = sum(queue_key(t) < queue_key(ticket) for _, t in others if t.get("stage") == f"{lane}-queued")
    room = count(lane) < cos_tick.LIMITS[lane] and count(*cos_state.ACTIVE) < cos_tick.CAP and not waiting
    op = {"op": "stage", "ticket": tid, "stage": lane if room else f"{lane}-queued", "status": "<status line>"}
    extra = []
    if caller == "conflict-stand":  # a merge run with no approval to carry: later head checks must not invent one
        op["set"] = {"noApproval": True}
        extra = ['set: {"noApproval": true}']
    if not room:
        return [f"stage: {json.dumps(op)}"], f"route: queue {lane}", 0
    parent, chief = ticket.get("parentThreadId"), state.get("chiefThreadId") or thread
    moving = MAY_NOT_HEAR.format(ticket=tid)
    if parent and parent != chief:
        return [f"fallback: if the continuation sends to the old child, add under Moving: {moving}"] + extra, f"route: continuation {lane}", 0
    return [f"stage: {json.dumps(op)}"] + ([f"moving: {moving}"] if not parent else []), f"route: send {lane}", 0


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"route: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="Where a relay goes: send now, queue, or continue.")
    ap.add_argument("ticket")
    ap.add_argument("caller", choices=sorted(ROUTES))
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--thread")
    args = ap.parse_args(argv)
    try:
        if not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        lines, last, code = route(load(args.file), args.ticket, args.caller, args.thread, project_config.review_after_conflict)
    except Cannot as e:
        print(f"route: cannot {e}")
        return 2
    print("\n".join([*lines, last]))
    return code


if __name__ == "__main__":
    sys.exit(main())
