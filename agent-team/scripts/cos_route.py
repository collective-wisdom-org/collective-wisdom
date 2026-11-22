#!/usr/bin/env python3
"""Where a relay goes: send now, queue, or start a continuation child (the Chief of Staff's "Send or queue").

Usage:
    ~/.collective-wisdom/scripts/cos_route.py <PREFIX>-N <caller> [--file STATE] [--thread ID] [--relay [--auto TOLERANCE [--risk TEXT]]] [--next]

Read only: sends nothing and writes no state. Reads the ticket from .agent-team/state.json (under the repo root unless
--file is given) through cos_state.load, the lane limits and cap from cos_tick.limits(), and, for the conflict callers,
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

The ticket's own slot does not count against it. The relay is sent when the lane is under its limit (merge: 1) and no ticket
waits ahead of it in the lane's queue (any queued ticket, or, for a ticket already in that queue, one with an older queuedAt;
a missing queuedAt sorts last, as in cos_tick), and, for the spec and build lanes, the spec and build count together is under
the cap (the merge lane is outside it); otherwise it is queued. A send to a ticket
whose parentThreadId is known and is not the Chief of Staff thread is a continuation instead (continuation.md).
Prints lines the caller acts on, then a last line, exit 0 unless noted:
    stage: <JSON stage op>                  to apply (a send: the lane's active stage; a queue: <lane>-queued, to which
                                            the caller adds pendingRelay and, for a user spec approval, approvalItemId)
    set: <JSON>                             a continuation has no stage op: add these keys to the lane's stage op
    moving: <line>                          copy under Moving (a send to a ticket with no known parent thread)
    merge-wait: <T>                         a merge-lane send: start the merge wait (cos_merge_wait.py)
    run-wait: <T>                           a spec or build send: start the run wait (cos_run_wait.py)
    fallback: <line>                        a continuation that falls back to sending to the old child adds this
                                            (also: start the merge wait in the merge lane, the run wait in spec or build)
    route: send <lane>                      send with t3_thread_send, then apply the stage op
    route: queue <lane>                     do not send; apply the stage op
    route: continuation <lane>              continuation.md § Continuation child, in place of the send
    route: no <why>                         (exit 1) the caller does not apply from this stage: do not send
    route: cannot <what>                    (exit 2) state unreadable or a bad argument

--relay prints the relay text after the last line (exit 0 only: nothing for `route: no`, and `route: cannot` replaces it), as a line
`relay:` and then the text, which runs to the end of the output. It is what send-or-queue.md § Send or queue sends or stores in
`pendingRelay`; for `queue` and `continuation` too. The user's words come on stdin, read once and used as they are (one trailing newline
dropped), and must not be empty. A caller with no relay text here prints no `relay:` block: `head-moved` and the `conflict-*` relays are
printed by cos_head_check.py, `reviewer-changes` is review.md's.
    approve-spec     CHIEF OF STAFF: the user approved the spec: "<words>". Continue to the build stage.
                     Approval in thread: <--thread>                      (--thread is required)
    approve-merge    CHIEF OF STAFF: the user approved the merge of PR #<ticket's pr> at head <first 7 of its headSha>: "<words>".
    changes          CHIEF OF STAFF: the user asked for changes: "<words>".
    answer           CHIEF OF STAFF: the user says: "<words>". Continue the <lane> stage.      (<lane>: the ticket's resumeStage)
    resume, rate-limit   CHIEF OF STAFF: continue the <lane> stage from where the branch is.   (no stdin)
--auto TOLERANCE (approve-spec and approve-merge only; reads no stdin) prints the auto-approval relay instead. --risk is the `<Level> (<reason>)`
text, `unrated` when left out:
    approve-spec     CHIEF OF STAFF: auto-approved the spec under `<TOLERANCE>` (Risk: <risk>). Continue to the build stage.
                     With TOLERANCE `No Hands`: CHIEF OF STAFF: auto-approved the spec under No Hands. Continue to the build stage.
    approve-merge    CHIEF OF STAFF: auto-approved the merge of PR #<pr> at head <short> under `<TOLERANCE>` (Risk: <risk>).

--next prints `next: <instruction>` after each line above whose action is fixed, from the NEXT table below (the `relay:` text gets none:
the route line says what to do with it). Without --relay and --next the output is unchanged.
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
# --next: the instruction after each line, by tag. Where send-or-queue.md § Send or queue used to hold this list.
NEXT = {
    "stage-send": "after the send, apply this stage op (fill in `status`): it clears pendingRelay, approvalItemId and queuedAt. Save it before the next line.",
    "stage-queue": "do not send. Apply this stage op (fill in `status`) with `pendingRelay` (the relay text) and, for a user spec approval, `approvalItemId` in `set`.",
    "set": "add these keys to the lane's stage op (a continuation has no stage op of its own).",
    "moving": "copy it under Moving.",
    "merge-wait": "start the merge wait for this ticket (sweep.md § Merge wait, cos_merge_wait.py).",
    "run-wait": "start the run wait for this ticket (sweep.md § Run wait, cos_run_wait.py).",
    "fallback": "if continuation.md § Continuation child falls back to sending to the old child, copy this line under Moving and start the wait it names.",
    "route-send": "t3_thread_send the relay to the ticket's child, then apply the stage op above.",
    "route-queue": "do not send: apply the stage op above.",
    "route-continuation": "continuation.md § Continuation child, in place of the send. If it falls back to sending to the old child, apply the lane's stage op with the `set:` line's keys.",
    "route-no": "the caller does not apply from this stage: do not send.",
    "route-cannot": "do not send, and tell the user under Needs you.",
}
NEXT_CALLER = {  # (tag, caller) -> text added to that tag's instruction
    ("route-send", "approve-spec"): " Run the models.md § Models switch (`t3_thread_configure` on that child) immediately before the send.",
    ("route-queue", "approve-spec"): " The models.md § Models switch runs just before the later send, not now.",
}
LINE_TAGS = (("stage: ", None), ("set: ", "set"), ("moving: ", "moving"), ("merge-wait: ", "merge-wait"), ("run-wait: ", "run-wait"), ("fallback: ", "fallback"))
RELAY_CALLERS = ("approve-spec", "approve-merge", "changes", "answer", "resume", "rate-limit")
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
    lane_limit, cap = cos_tick.limits()
    room = count(lane) < lane_limit[lane] and (lane == "merge" or count("spec", "build") < cap) and not waiting
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
        start = f" and start the {'merge' if lane == 'merge' else 'run'} wait"
        return [f"fallback: if the continuation sends to the old child, add under Moving: {moving}{start}"] + extra, f"route: continuation {lane}", 0
    wait = [f"{'merge' if lane == 'merge' else 'run'}-wait: {tid}"]
    return [f"stage: {json.dumps(op)}"] + ([f"moving: {moving}"] if not parent else []) + wait, f"route: send {lane}", 0


def tag_of(line, last):
    """The NEXT tag of an output line (last is the route line), or None."""
    if line.startswith("route: "):
        kind = line.split()[1]
        return f"route-{kind}" if f"route-{kind}" in NEXT else None
    for prefix, tag in LINE_TAGS:
        if line.startswith(prefix):
            return tag or ("stage-send" if last.startswith("route: send") else "stage-queue")
    return None


def next_text(line, last, caller):
    tag = tag_of(line, last)
    return None if tag is None else NEXT[tag] + NEXT_CALLER.get((tag, caller), "")


def relay_text(state, tid, caller, lane, thread, auto, risk, read_words):
    """The relay text for the caller (see the docstring), or None for a caller with none. read_words() gives the user's words."""
    if caller not in RELAY_CALLERS:
        return None
    if auto is not None and caller not in ("approve-spec", "approve-merge"):
        raise Cannot(f"give --auto only to approve-spec or approve-merge, not {caller}")
    if caller in ("resume", "rate-limit"):
        return f"CHIEF OF STAFF: continue the {lane} stage from where the branch is."
    ticket = state["tickets"][tid]
    if caller == "approve-merge":
        pr, head = ticket.get("pr"), ticket.get("headSha")
        if not (isinstance(pr, int) and not isinstance(pr, bool) and isinstance(head, str) and len(head) >= 7):
            raise Cannot(f"read pr and headSha of {tid} for the merge relay")
        at = f"the merge of PR #{pr} at head {head[:7]}"
    if auto is not None:
        if not auto.strip():
            raise Cannot("give --auto a tolerance")
        if caller == "approve-spec":
            if auto == "No Hands":
                return "CHIEF OF STAFF: auto-approved the spec under No Hands. Continue to the build stage."
            return f"CHIEF OF STAFF: auto-approved the spec under `{auto}` (Risk: {risk or 'unrated'}). Continue to the build stage."
        return f"CHIEF OF STAFF: auto-approved {at} under `{auto}` (Risk: {risk or 'unrated'})."
    words = read_words()
    if not words.strip():
        raise Cannot("read the user's words on stdin")
    if caller == "approve-spec":
        if not thread:
            raise Cannot("give --thread for a spec approval relay")
        return f'CHIEF OF STAFF: the user approved the spec: "{words}". Continue to the build stage.\nApproval in thread: {thread}'
    if caller == "approve-merge":
        return f'CHIEF OF STAFF: the user approved {at}: "{words}".'
    if caller == "changes":
        return f'CHIEF OF STAFF: the user asked for changes: "{words}".'
    return f'CHIEF OF STAFF: the user says: "{words}". Continue the {lane} stage.'


class Parser(argparse.ArgumentParser):
    want_next = False

    def error(self, message):
        print(f"route: cannot {message}")
        if self.want_next:
            print(f"next: {NEXT['route-cannot']}")
        raise SystemExit(2)


def main(argv=None):
    Parser.want_next = "--next" in (sys.argv[1:] if argv is None else argv)
    ap = Parser(description="Where a relay goes: send now, queue, or continue.")
    ap.add_argument("ticket")
    ap.add_argument("caller", choices=sorted(ROUTES))
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--thread")
    ap.add_argument("--relay", action="store_true")
    ap.add_argument("--auto")
    ap.add_argument("--risk")
    ap.add_argument("--next", action="store_true")
    args = ap.parse_args(argv)
    try:
        if not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        if (args.auto is not None or args.risk is not None) and not args.relay:
            raise Cannot("use --auto and --risk with --relay")
        if args.risk is not None and args.auto is None:
            raise Cannot("use --risk with --auto")
        state = load(args.file)
        lines, last, code = route(state, args.ticket, args.caller, args.thread, project_config.review_after_conflict)
        relay = None
        if args.relay and code == 0:
            lane = last.split()[-1]
            relay = relay_text(state, args.ticket, args.caller, lane, args.thread, args.auto, args.risk,
                               lambda: sys.stdin.read().removesuffix("\n").removesuffix("\r"))
    except Cannot as e:
        print(f"route: cannot {e}")
        if args.next:
            print(f"next: {NEXT['route-cannot']}")
        return 2
    for line in [*lines, last]:
        print(line)
        if args.next and (text := next_text(line, last, args.caller)):
            print(f"next: {text}")
    if relay:
        print(f"relay:\n{relay}")
    return code


if __name__ == "__main__":
    sys.exit(main())
