#!/usr/bin/env python3
"""Read and edit the Chief of Staff state file, so nobody prints or rewrites it by hand.

Usage:
    ~/.collective-wisdom/scripts/cos_state.py [--file PATH] show
    ~/.collective-wisdom/scripts/cos_state.py [--file PATH] get GORP-N | --pm
    ~/.collective-wisdom/scripts/cos_state.py [--file PATH] apply < ops.json
    ~/.collective-wisdom/scripts/cos_state.py [--file PATH] prune
    ~/.collective-wisdom/scripts/cos_state.py [--file PATH] init
    ~/.collective-wisdom/scripts/cos_state.py now [--iso]
    ~/.collective-wisdom/scripts/cos_state.py title <PREFIX>-N                       the raw ticket title on stdin
    ~/.collective-wisdom/scripts/cos_state.py comment approved <spec|merge> [--head SHA] [--queued LANE]      the user's words on stdin
    ~/.collective-wisdom/scripts/cos_state.py comment auto <spec|merge> --tolerance T [--head SHA] [--queued LANE]   `<Level> (<reason>)` on stdin, or nothing
    ~/.collective-wisdom/scripts/cos_state.py comment withdrawn                      the reason on stdin

--file defaults to .agent-team/state.json under the repo root this script lives in.
show prints the working set (a few lines plus one status line per ticket). get prints
one ticket (or the pm block) as JSON. apply reads a JSON list of operations on stdin and
applies all of them or none: it prints "unchanged", or "saved" and one line per changed
ticket, and writes through a temp file, fsync and os.replace under a flock on state.lock
next to the file. After either result, a start, merged or drop op also removes its ticket from the saved Todo and
Backlog lists (tracker-lists.json next to the file, through cos_lists.remove) so the dashboard stops showing it; that
never changes the output or the exit code. init writes an empty state file if there is none. prune drops old merged entries, observed entries older than 7 days and unknown top-level keys.
now prints the current time as 2026-11-15 5:16 am UTC (--iso: 2026-11-15T05:16:00Z) and reads no state file; it is the only
source of a clock time the Chief of Staff writes into a ticket comment.

title and comment read no state file. Both print the finished text, one line, and nothing else; the caller copies it.
title prints the display text of a ticket in a message to the user: `<PREFIX>-N: <short title>`. The title is ticket-author text, so
`[`, `]`, `<`, `>`, backticks and control characters (newlines included) become spaces, runs of white space collapse, and the first six words are kept.
It prints the ID alone when nothing is left, or when the title (before the cut to six words) contains a marker, so it cannot pass for one:
`Auto-approved`, `SPEC READY`, `BUILD READY`, `MERGE READY`, `BLOCKED:`, `MERGED #` or `CHIEF OF STAFF:`, ignoring case, white space, the dropped
characters and hyphens of any kind (- ‐ ‑ ‒ – — ― − and the soft hyphen).
comment prints the ticket comment for an approval, with every <time> from `now` (2026-11-15 5:16 am UTC):
    approved   the user approved the <spec|merge> at <time>: "<words>". Head <sha>.     (` Head <sha>.` only for a merge, which needs --head)
    auto       auto-approved the <spec|merge> at <time> under <T> (Risk: <Level> (<reason>)).    (` Head <sha>.` added for a merge; no stdin: Risk: unrated)
    withdrawn  Approval withdrawn at <time>: <reason>.                                    (a final `.` is added when the reason has none)
--queued LANE (spec, build or merge; approved and auto only) ends the comment with ` Waiting for a <lane> slot.`
--head SHA is 7 to 40 hex characters and is a merge-only option. The stdin text is trimmed; words (approved) and reason (withdrawn) are required.
Exit 0 prints the text. Exit 2: bad arguments or empty stdin, with a `cos_state: ...` line on stderr and nothing on stdout.

A status line takes its since time from the script: {since} in the text of a start, stage or set op becomes the ticket's
stageAt as 2026-11-15 5:16 am UTC. A status with since followed by a digit before its first ": " (a hand-typed time) is rejected; text after it is left alone.

Operations (each {"op": NAME, ...}):
    start     ticket, firstTaskId, childThreadId, parentThreadId, status, title; optional branch
    stage     ticket, stage, status; optional set (a stage change needs a status line)
              awaiting-build, awaiting-review, awaiting-merge and blocked stamp lastSeenAt (the cut-off for the
              user's approve N) on entry, on a new headSha and when a heldApproval is withdrawn. One exception: awaiting-review to awaiting-merge
              with headSha unchanged keeps it. awaiting-review holds no lane slot.
              start and a stage op that changes the stage stamp stageAt; a set or stage op naming it is rejected.
    set       ticket, set (ticket fields other than stage)
    merged    ticket, pr
    drop      ticket
    top       set (top-level keys other than tickets, merged, pm, lastRelayAt); also drops a leftover
              rotation or rotationHeldUntil (keys of the old thread rotation) from the state
    pm        set
    observe   kind; optional ticket. Records a sighting and prints a note: file (start an
              observation ticket helper) or hold. The only op that writes "observed".
              Kind, by the report line that shows it: lost-notice (`found by the sweep`, `... idle check`,
              `... merged check`); handoff-unavailable (`Handoff block unavailable for <PREFIX>-N: <short title>`);
              wait-check-unreadable (`<PREFIX>-N: <short title>, wait check unreadable; not blocked`); stall
              (`<PREFIX>-N: <short title>, restarted: stalled after <step>`); rotation-failed (`Reset refused: <error>`);
              helper-no-report (`Ticket helper ended without a report`); script-unavailable (`Idle check didn't run`,
              `User check script unavailable; used thread read`, or a sweep or check that exited 2); other:<slug>
              (anything else you can point to, such as a step that cost a second run; slug is 1 to 40 lowercase
              letters, digits and hyphens).
    prune
    no-hands  set (a fresh No Hands run record, or drain, or endedAt with endReason). Only no_hands.py uses it; no other op writes "noHands".

heldApproval ({"head", "itemId", "at"}: the user's approve N, held until a teammate approves) is allowed only
in awaiting-review, must carry a full head and an itemId, and its head must equal the ticket's headSha. The op sends head and itemId; the script
stamps at, and an op that names at is rejected. A new headSha and a stage op to any other
stage clear it; setting it in another stage is rejected.

changesRelayed ({"head", "at"}: the head and time a reviewer's changes request was sent back to the child) may be
set in any stage and is never cleared by the script; null clears it. It must be an object with a full 40-hex
head and an at time with a zone (2026-11-02T10:00:00Z), or the op is rejected.

conflictHead (a full 40-hex SHA, or null) is the PR head a merge conflict was last sent back to the child for. It may be set
in any stage and is never cleared by the script; the ready check does not flag the same head twice. Anything else is rejected.

noApproval (true only) marks a merge-lane run that carries no user approval (a conflict sent to the merge lane while
reviews stand). It is allowed only in merge, merge-queued and blocked, and a stage op to any other stage clears it.

noHands is the No Hands run record: {"startedAt", "itemId", "started", "drain", "endedAt", "endReason"}. The no-hands op
allows only the moves no_hands.py makes: a whole fresh record (started [], the rest null, a new itemId, a startedAt later than
the last run's endedAt) when no run is active (none, or endedAt set); a drain string on an active run with none yet; endedAt (with a time zone) and endReason together on an active
run. Anything else is rejected, so an ended run stays ended and itemId and started never change through it. The start op
appends its ticket to started while a run has no endedAt.

chiefProvider ({"threadId", "provider"}, both plain strings) is the provider (T3's providerInstanceId) of the Chief of Staff
thread that recorded it; the top op sets it. The ticket field provider (a string, or null) is the provider of the ticket's
child thread, set from a thread read. cos_tick.py compares them to flag a child on another harness.

ganttPluginVersion is the agent-gantt version this Chief of Staff session runs: a string of dot-separated integers (0.1.12), or null.

reset is null, or the marker of a session reset in flight: {"id" (8 hex chars), "startedAt" (a time with a zone), "reason" (a
non-empty string), optional "mode" (reset, reset-scheduled or compact)}. lastResetAt is a time with a zone, or null. The top op
rejects any other shape.

takeover is null, or the marker of a take over (or resume) pass in progress: {"startedAt" (a time with a zone, not in the
future), "mode" (take-over or resume)}. The top op rejects any other shape. show prints it as takeover=<mode> since <time>.

Exit codes: 0 ok, 1 an op was rejected ("cos_state: op <i>: <reason>") or no such
ticket, 2 the state file is missing or unreadable.

State file example (.agent-team/state.json). Top-level keys are exactly the ones below (TOP), a ticket holds only the keys below (TICKET);
never add `policy`, `settings`, `rules` or the like. `prune` drops an unknown top-level key and `show` prints them as `unknown keys:`.
    {
      "paused": false, "chiefThreadId": "...", "chiefSessionId": "...",
      "chiefProvider": {"threadId": "...", "provider": "<provider id>"},
      "takeoverContext": {"threadId": "...", "tokens": 76000}, "skillCommit": "<40-char sha>", "ganttPluginVersion": "0.1.12",
      "reset": null, "takeover": null, "lastResetAt": null, "lastRelayAt": null,
      "rateLimitedAt": null, "wakeTaskId": null, "wakeAt": null,
      "merged": {"<PREFIX>-190": {"pr": 178, "at": "2026-11-02T09:30:00Z"}},
      "tickets": {"<PREFIX>-210": {
        "stage": "spec", "firstTaskId": "...", "childThreadId": "...", "parentThreadId": "...",
        "status": "spec since 2026-11-01 2:05 pm UTC: child started; no BUILD READY yet.",
        "title": "Example feature", "provider": "<provider id>", "branch": "feat/<prefix>-210-example-feature",
        "specPath": null, "specSha": null, "pr": null, "headSha": null, "rateLimitResumes": 0,
        "lastSeenAt": "2026-11-01T14:05:00Z", "lastPosition": 0, "resumeStage": null,
        "pendingRelay": null, "approvalItemId": null, "queuedAt": null,
        "restarts": {"spec": 0}, "note": "", "stageAt": "2026-11-01T14:05:00Z"}},
      "observed": {"sightings": [{"kind": "stall", "ticket": "<PREFIX>-210", "at": "2026-11-02T09:30:00Z"}], "filed": []},
      "pm": {},
      "noHands": {"startedAt": "2026-11-08T09:00:00Z", "itemId": "...", "started": ["<PREFIX>-210"], "drain": null, "endedAt": null, "endReason": null}
    }

What each key means and who writes it (what the ops validate and stamp is above):
    note          status only (why it is blocked, who stopped it), never an instruction or a rule.
    branch        `<head><prefix>-N-<slug>`; the example uses `feat/`, `infra/` too when the `Branch pattern` row of docs/agents/project.md lists it.
    resumeStage   set by apply when a ticket moves to `blocked` from `spec`, `build` or `merge`; every path out of `blocked` goes back to it
                  through send-or-queue.md § Send or queue.
    pendingRelay, queuedAt   only in a `*-queued` stage (apply requires pendingRelay there, sets queuedAt, clears both elsewhere).
                  pendingRelay is the exact relay to send when a slot frees, with the user's words as written; queuedAt orders the queue,
                  oldest first. A Todo ticket has no child yet: it waits in the spec queue (SKILL.md § Lanes) with no stage.
    approvalItemId   item id (from cos_user_check.py or t3_thread_read) of the user's approval message; set with pendingRelay when a spec
                  approval is queued. A queued merge approval or an auto-approved spec has none.
    lastSeenAt    in awaiting-build, awaiting-review, awaiting-merge and blocked, the cut-off after which the user's `approve N` counts
                  (stamped here; a `set` is rejected). In spec, build and merge, the Stop hook's `late-child:` line compares it with the
                  child's newest run end and pending questions; a `child-read` save of it quiets that line.
    stageAt       when the ticket entered its stage (stamped here). The status card shows `waiting ...` in `awaiting-*` only.
    changesRelayed   set when a reviewer's changes request was relayed to the child (sweep.md § Sweep, `changes` line); `at` is the newest
                  CHANGES_REQUESTED review time sent, as the `changes` line prints it. cos_review_check.py prints `changes` for a request
                  on the head only when it is newer, so one the child already answered reads as `waiting`. null or absent: nothing relayed.
    conflictHead  the PR head a merge conflict was last sent back to the child for (sweep.md § Conflict relay). While the PR head equals
                  it the ready check prints `building <PREFIX>-N #PR (conflict relayed)` instead of `conflict`: one relay per head.
    noApproval    true: a merge-lane run with no user approval (a `MERGE READY` conflict sent by `conflict-stand`). The head check reads
                  it, so such a ticket never gets `conflict keep`.
    heldApproval  set when the user replies `approve N` on an `awaiting-review` ticket. A reminder only, never the proof: cos_approve_pr.py
                  still finds the user's own `approve N` after lastSeenAt. A rebuild never restores it.
    title         the ticket title, required by the `start` op; the dashboard shows it when it cannot read the tracker. A `set` may fill it;
                  the script cleans it (ticket-author text) and keeps 200 characters.
    chiefThreadId the current Chief of Staff thread. Written by "start the team" and resume mode, never by a reset (the thread stays).
    chiefProvider the provider (providerInstanceId) of the thread that recorded it; saved by startup.md step 3 and resume mode (rotation.md
                  § Thread rotation: Resume mode) with a `top` op. A missing one, or one naming another thread, prints `chief-provider` in
                  the look plan (SKILL.md § Tick). Plain strings that go into plan lines: cos_tick.py stops the plan on an unsafe one.
    provider      a ticket's `thread.providerInstanceId` of its child from the last `child-read` or idle check that returned one; a
                  different one is saved with a `set` op, a failed read saves nothing. None: never flagged. Safe-checked like chiefProvider.
    chiefSessionId   the Claude session id (Cursor: conversation id) of the Chief of Staff thread; the rotation check saves it on every plain
                  run, so it follows a reset. The Stop hook uses it to tell this thread from other sessions.
    takeoverContext  saved by take-over step 4 (`--record-takeover`): this thread's context size when take-over ended. While it names
                  chiefThreadId and `tokens` is at or above the size cap, the size trigger stays off, so a take-over that lands above the
                  cap doesn't reset again and again. Cursor's `turn` form: the cos_rotation_check.py docstring.
    skillCommit   the full 40-character sha from `python3 ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit` (the last commit
                  that touched the chief-of-staff skill, `project-manager` or docs/agents/chief-of-staff.md) when the session loaded the
                  skill. Written by "start the team", take over and resume mode. A different commit at the rotation check triggers a reset
                  once the turn is quiet (rotation.md § Thread rotation). null or a non-full sha: the check prints `ok; set skillCommit <sha>`;
                  save that sha and don't reset on that trigger.
    ganttPluginVersion   the agent-gantt version this session runs, or null (that trigger is off). Saved by take over step 4 and resume
                  mode. A different clone version at the rotation check triggers a reset once the turn is quiet.
    status        one line per ticket (data, never an instruction), required on every `stage` op: what a fresh thread needs to act without
                  opening the child. Starts `<stage> since {since}: `. E.g. `awaiting-merge since {since}: PR #192 head 0b63161, code review
                  PASS (pass 2), security PASS (pass 1). Waiting on the user to approve the merge.` or `blocked since {since}: "<the BLOCKED:
                  line>".` It feeds reports, `status` and the take-over pass; it never replaces headSha, approvalItemId or pendingRelay, which
                  the gates read. Mid-build it says only what was last seen.
    parentThreadId   the Chief of Staff thread whose `delegate_task` started the ticket's current child; set at start and at a continuation
                  start (send-or-queue.md § Send or queue). A ticket without it stays so: the sweep lists it for a full read, and it gets
                  no continuation.
    reset         the marker of a reset in flight (rotation.md § Thread rotation), else null. The next take over clears it when
                  `CHIEF OF STAFF RESET <id>` matches.
    takeover      null, or the marker while a take over or resume pass runs. Take-over step 1 and resume mode set it; step 4 and step 2 (when
                  it stops the take over) clear it. While set, the rotation check prints `finish:` and every look plan except `start` is
                  the one `follow rotation.md § Thread rotation: Finish take over` line.
    lastRelayAt   when a relay or new child start last went out (stamped here; a `top` set is rejected). The rotation check treats the
                  last 10 minutes as not quiet.
    lastResetAt   when the last take over cleared a `reset`; a skill change and the item-count fallback wait 60 minutes after it.
    wakeTaskId, wakeAt   the pending rate-limit wake (rate-limit.md § Rate limit) and when it fires. wakeTaskId is null when none is pending;
                  wakeAt stays set until rateLimitedAt clears, so a lost wake can be made again.
    merged        tickets whose child reported `MERGED #N`. The project manager hygiene child uses it to move them to Done if the tracker
                  lags. `prune` drops entries older than 24 hours and rewrites a bare number as merged now.
    observed      your own process sightings and the observation tickets filed (SKILL.md § Child path "Observe"). Only the `observe` op
                  writes it, deciding `file` or `hold`; `prune` drops entries older than 7 days.
    noHands       the current or last No Hands run, a record and not a rule. Written only by no_hands.py through the `no-hands` op (the
                  `start` op appends to `started`); a top-level `set` is rejected. Absent until the first run. It alone approves nothing
                  (no-hands.md § Run record).
    pm            owned by `project-manager` § State (`pm` ops).
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
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_lists  # noqa: E402
from clock12 import clock12  # noqa: E402
import project_config  # noqa: E402

DEFAULT_FILE = root() / ".agent-team" / "state.json"
TOP = {
    "paused", "chiefThreadId", "chiefSessionId", "takeoverContext", "skillCommit",
    "ganttPluginVersion", "reset", "takeover", "lastResetAt", "lastRelayAt", "rateLimitedAt", "wakeTaskId", "wakeAt",
    "merged", "tickets", "pm", "observed", "noHands", "chiefProvider",
}
TICKET = {
    "stage", "firstTaskId", "childThreadId", "parentThreadId", "status", "branch", "specPath",
    "specSha", "pr", "headSha", "rateLimitResumes", "lastSeenAt", "lastPosition", "resumeStage",
    "pendingRelay", "approvalItemId", "queuedAt", "restarts", "note", "heldApproval", "changesRelayed", "conflictHead", "title",
    "noApproval", "provider", "stageAt",
}
STAGES = (
    "spec", "awaiting-build", "spec-queued", "build-queued", "build",
    "awaiting-review", "awaiting-merge", "merge-queued", "merge", "blocked",
)
ACTIVE = ("spec", "build", "merge")
PM = {
    "lastCheckAt", "lastDailyAt", "ranked", "rankedAt", "rankedReady", "needsReported", "filled",
    "flaggedDuplicates", "flaggedStale",
}
ID = project_config.ticket_re(anchored=True)
DAY = timedelta(hours=24)
WEEK = timedelta(days=7)
KINDS = (
    "lost-notice", "handoff-unavailable", "wait-check-unreadable", "stall", "rotation-failed",
    "helper-no-report", "script-unavailable",
)
SLUG = re.compile(r"[a-z0-9-]{1,40}")


class Reject(Exception):
    pass


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_text(iso):
    """2026-11-15 5:16 am UTC for an ISO time with a zone: the one clock-time format status lines and comments use."""
    d = parse(iso).astimezone(timezone.utc)
    return f"{d:%Y-%m-%d} {clock12(d)} UTC"


def parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def older_than_day(s):
    t = parse(s)
    return t is not None and datetime.now(timezone.utc) - t > DAY


def within(s, delta):
    t = parse(s)
    return t is not None and datetime.now(timezone.utc) - t <= delta


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


BAD_TITLE = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]+")


def clean_title(val):
    """A ticket title is untrusted and drawn in a terminal pane: control characters become spaces, 200 characters at most."""
    if not isinstance(val, str):
        raise Reject("title must be a string")
    return BAD_TITLE.sub(" ", val).strip()[:200]


TITLE_DROP = re.compile(r"[\[\]<>`\x00-\x1f\x7f-\x9f\u2028\u2029]")
TITLE_WORDS = 6
# What a title may not contain: each marker is compared with case, white space, hyphens of any kind and the dropped characters ignored.
TITLE_MARKERS = ("autoapproved", "specready", "buildready", "mergeready", "blocked:", "merged#", "chiefofstaff:")
HYPHENS = re.compile("[-\u00ad\u2010-\u2015\u2212\ufe58\ufe63\uff0d]")


def title_has_marker(raw):
    # fold look-alikes first: NFKD (fullwidth letters, accents split off), then drop invisible format characters, combining marks and blank fillers
    raw = "".join(c for c in unicodedata.normalize("NFKD", raw) if unicodedata.category(c) not in ("Cf", "Mn", "Me") and c not in "\u3164\u115f\u1160\u2800")
    flat = HYPHENS.sub("", raw).lower()
    for text in (flat, TITLE_DROP.sub("", flat)):
        text = re.sub(r"\s+", "", text)
        if any(m in text for m in TITLE_MARKERS):
            return True
    return False


def display_title(tid, raw):
    """`<ID>: <first six words of the cleaned title>`, or the ID alone for an empty title or one that carries a marker."""
    words = TITLE_DROP.sub(" ", raw).split()
    if not words or title_has_marker(raw):
        return tid
    return f"{tid}: {' '.join(words[:TITLE_WORDS])}"


LANES = ("spec", "build", "merge")
HEAD = re.compile(r"[0-9a-fA-F]{7,40}")


def approval_comment(kind, what, text, head, queued, tolerance, time):
    """The ticket comment text for `comment`, always one line (white space in the words collapses). Raises Reject for a bad combination of arguments."""
    text = " ".join((text or "").split())
    if kind == "withdrawn":
        if what or head or queued or tolerance:
            raise Reject("withdrawn takes only the reason on stdin")
        if not text:
            raise Reject("withdrawn needs the reason on stdin")
        return f"Approval withdrawn at {time}: {text}" + ("" if text.endswith(".") else ".")
    if what not in ("spec", "merge"):
        raise Reject(f"{kind} needs spec or merge")
    if (what == "merge") != bool(head):
        raise Reject("--head is for a merge, and a merge needs it")
    if head and not HEAD.fullmatch(head):
        raise Reject("--head needs 7 to 40 hex characters")
    if queued is not None and queued not in LANES:
        raise Reject(f"--queued needs one of {', '.join(LANES)}")
    tail = (f" Head {head}." if head else "") + (f" Waiting for a {queued} slot." if queued else "")
    if kind == "approved":
        if tolerance or not text:
            raise Reject("approved needs the user's words on stdin and takes no --tolerance")
        return f'the user approved the {what} at {time}: "{text}".{tail}'
    if not tolerance or not tolerance.strip():
        raise Reject("auto needs --tolerance")
    return f"auto-approved the {what} at {time} under {tolerance.strip()} (Risk: {text or 'unrated'}).{tail}"


HAND_TIME = re.compile(r"since\s*\d")


def fill_status(text, stage_at):
    """Replace {since} with the stageAt time; reject a hand-typed since time before the first ": " (the rest, a Risk: reason or a quoted line, is left alone)."""
    if not isinstance(text, str):
        return text
    if HAND_TIME.search(text.split(": ", 1)[0]):
        raise Reject("status: write since {since}, not a time; the script fills it from stageAt")
    return text.replace("{since}", stamp_text(stage_at or now()))


def merge_set(t, sets):
    """t.update(sets), but a dict value for restarts merges into the existing counts and heldApproval gets its at stamped."""
    for k, val in sets.items():
        if k == "title":
            val = clean_title(val)
        if k == "heldApproval" and isinstance(val, dict):
            if "at" in val:
                raise Reject("heldApproval at is stamped by the script")
            val = {**val, "at": now()}
        if k == "restarts" and isinstance(val, dict) and isinstance(t.get(k), dict):
            t[k] = {**t[k], **val}
        else:
            t[k] = val


def ticket_of(s, op):
    tid = op.get("ticket")
    if not isinstance(tid, str) or not ID.fullmatch(tid):
        raise Reject(f"bad ticket id {tid!r}")
    return tid, s["tickets"].get(tid)


def check(t):
    queued = t["stage"].endswith("-queued")
    if queued and not t.get("pendingRelay"):
        raise Reject(f"stage {t['stage']} needs pendingRelay")
    if not queued and (t.get("pendingRelay") or t.get("queuedAt")):
        raise Reject(f"pendingRelay and queuedAt only belong to a queued stage, not {t['stage']}")
    relayed = t.get("changesRelayed")
    if relayed is not None and not (
        isinstance(relayed, dict) and isinstance(relayed.get("head"), str) and re.fullmatch(r"[0-9a-f]{40}", relayed["head"])
        and getattr(parse(relayed.get("at")), "tzinfo", None) is not None
    ):
        raise Reject("changesRelayed needs an object with a full head and an at time with a zone")
    conflict_head = t.get("conflictHead")
    if conflict_head is not None and not (isinstance(conflict_head, str) and re.fullmatch(r"[0-9a-f]{40}", conflict_head)):
        raise Reject("conflictHead needs a full 40-hex head or null")
    if "noApproval" in t:
        if t["noApproval"] is not True:
            raise Reject("noApproval must be true")
        if t["stage"] not in NO_APPROVAL_STAGES:
            raise Reject(f"noApproval only belongs to merge, merge-queued or blocked, not {t['stage']}")
    held = t.get("heldApproval")
    if held:
        if t["stage"] != "awaiting-review":
            raise Reject(f"heldApproval only belongs to awaiting-review, not {t['stage']}")
        if not (
            isinstance(held, dict) and isinstance(held.get("head"), str) and re.fullmatch(r"[0-9a-f]{40}", held["head"])
            and held.get("itemId") and held.get("at")
        ):
            raise Reject("heldApproval needs an object with a full head and itemId")
        if held["head"] != t.get("headSha"):
            raise Reject("heldApproval head must equal the ticket's headSha")


def op_start(s, op):
    need(op, "ticket", "firstTaskId", "childThreadId", "parentThreadId", "status", "title", optional=("branch",))
    title = clean_title(op["title"])
    if not title:
        raise Reject("title must be a non-empty string")
    tid, t = ticket_of(s, op)
    if t:
        if t.get("childThreadId") != op["childThreadId"]:
            raise Reject(f"{tid} already exists with another childThreadId")
        return
    stamp = now()
    s["tickets"][tid] = {
        "stage": "spec", "firstTaskId": op["firstTaskId"], "childThreadId": op["childThreadId"],
        "parentThreadId": op["parentThreadId"], "status": fill_status(op["status"], stamp),
        "branch": op.get("branch"), "title": title, "specPath": None, "specSha": None, "pr": None,
        "headSha": None, "rateLimitResumes": 0, "lastSeenAt": now(), "lastPosition": 0,
        "resumeStage": None, "pendingRelay": None, "approvalItemId": None, "queuedAt": None,
        "restarts": {"spec": 0}, "note": "", "stageAt": stamp,
    }
    s["lastRelayAt"] = now()
    run = s.get("noHands")
    if isinstance(run, dict) and run.get("startedAt") and not run.get("endedAt") and tid not in run.get("started", []):
        run["started"] = [*run.get("started", []), tid]


NO_APPROVAL_STAGES = ("merge", "merge-queued", "blocked")
STAMPED = ("awaiting-build", "awaiting-review", "awaiting-merge", "blocked")  # lastSeenAt here is the approval cut-off


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
    if "stageAt" in sets:
        raise Reject("stageAt is stamped by the script")
    if new in STAMPED and "lastSeenAt" in sets:
        raise Reject(f"lastSeenAt is stamped by the script in {new}")
    new_child = sets.get("childThreadId") not in (None, t.get("childThreadId"))
    if new == "blocked" and old in ACTIVE:
        t["resumeStage"] = old
    elif old == "blocked" and new != "blocked":
        t["resumeStage"] = None
    if not new.endswith("-queued"):
        t.update(pendingRelay=None, approvalItemId=None, queuedAt=None)
    had_held = bool(t.get("heldApproval"))
    if new != "awaiting-review":
        t.pop("heldApproval", None)
    if new not in NO_APPROVAL_STAGES:
        t.pop("noApproval", None)
    old_head = t.get("headSha")
    merge_set(t, sets)
    if t.get("headSha") != old_head and "heldApproval" not in sets:
        t.pop("heldApproval", None)
    head_same = t.get("headSha") == old_head
    # awaiting-review to awaiting-merge on the same head keeps the cut-off: the user saw that head's merge block on entry.
    kept = old == "awaiting-review" and new == "awaiting-merge" and head_same
    withdrawn = new == "awaiting-review" and had_held and not t.get("heldApproval")  # the user's approve N no longer counts
    if new in STAMPED and (new != old or not head_same or withdrawn) and not kept:  # a new head voids an approval cut-off
        t["lastSeenAt"] = now()
    t.update(stage=new, status=op["status"])
    if new != old:
        t["stageAt"] = now()
    t["status"] = fill_status(op["status"], t.get("stageAt"))
    if new in ACTIVE and (new != old or new_child):  # a continuation start keeps the lane
        s["lastRelayAt"] = now()
    if new.endswith("-queued") and (new != old or not t.get("queuedAt")):
        t["queuedAt"] = now()
    check(t)


def op_set(s, op):
    need(op, "ticket", "set")
    tid, t = ticket_of(s, op)
    if not t:
        raise Reject(f"no ticket {tid}")
    keys_ok(op["set"], TICKET - {"stage"}, "ticket")
    if "stageAt" in op["set"]:
        raise Reject("stageAt is stamped by the script")
    if t["stage"] in STAMPED and "lastSeenAt" in op["set"]:
        raise Reject(f"lastSeenAt is stamped by the script in {t['stage']}")
    if t["stage"] in ACTIVE and op["set"].get("childThreadId") not in (None, t.get("childThreadId")):
        s["lastRelayAt"] = now()
    old_head, had_held = t.get("headSha"), bool(t.get("heldApproval"))
    merge_set(t, op["set"])
    if "status" in op["set"]:
        t["status"] = fill_status(op["set"]["status"], t.get("stageAt"))
    if t.get("headSha") != old_head and "heldApproval" not in op["set"]:
        t.pop("heldApproval", None)
    withdrawn = had_held and not t.get("heldApproval")  # the user's approve N no longer counts
    if t["stage"] in STAMPED and (t.get("headSha") != old_head or withdrawn):  # a new head voids an approval cut-off
        t["lastSeenAt"] = now()
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
    keys_ok(op["set"], TOP - {"tickets", "merged", "pm", "lastRelayAt", "observed", "noHands"}, "top-level")
    zoned = lambda x: isinstance(x, str) and getattr(parse(x), "tzinfo", None) is not None  # noqa: E731
    sane = lambda x: zoned(x) and parse(x) <= datetime.now(timezone.utc) + timedelta(minutes=5)  # noqa: E731  # a future time would hold resets for good
    marker = op["set"].get("reset")
    if marker is not None:
        if not (
            isinstance(marker, dict) and set(marker) <= {"id", "startedAt", "reason", "mode"}
            and isinstance(marker.get("id"), str) and re.fullmatch(r"[0-9a-f]{8}", marker["id"])
            and sane(marker.get("startedAt")) and isinstance(marker.get("reason"), str) and marker["reason"]
            and marker.get("mode", "reset") in ("reset", "reset-scheduled", "compact")
        ):
            raise Reject("reset needs null, or an id (8 hex chars), a startedAt with a zone (not in the future) and a reason, and optionally a mode")
    take = op["set"].get("takeover")
    if take is not None and not (
        isinstance(take, dict) and set(take) == {"startedAt", "mode"} and sane(take["startedAt"]) and take["mode"] in ("take-over", "resume")
    ):
        raise Reject("takeover needs null, or a startedAt with a zone (not in the future) and a mode (take-over or resume)")
    if op["set"].get("lastResetAt") is not None and not sane(op["set"]["lastResetAt"]):
        raise Reject("lastResetAt needs a time with a zone, not in the future, or null")
    sha = op["set"].get("skillCommit")
    if "skillCommit" in op["set"] and sha is not None and not (isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha)):
        raise Reject("skillCommit needs the full 40-character sha from cos_rotation_check.py --skill-commit, or null")
    ver = op["set"].get("ganttPluginVersion")
    if ver is not None and not (isinstance(ver, str) and re.fullmatch(r"\d+(\.\d+)*", ver)):
        raise Reject("ganttPluginVersion needs dot-separated integers like 0.1.12, or null")
    s.update(op["set"])
    for old in ("rotation", "rotationHeldUntil"):  # keys of the thread rotation this replaced
        s.pop(old, None)


NO_HANDS = ("startedAt", "itemId", "started", "drain", "endedAt", "endReason")


def op_no_hands(s, op):
    """The moves no_hands.py makes: a fresh record when no run is active, a drain reason, or the end (endedAt with endReason)."""
    need(op, "set")
    new = op["set"]
    keys_ok(new, set(NO_HANDS), "noHands")
    cur = s.get("noHands") if isinstance(s.get("noHands"), dict) else {}
    live = bool(cur.get("startedAt")) and not cur.get("endedAt")
    zoned = lambda x: isinstance(x, str) and getattr(parse(x), "tzinfo", None) is not None  # noqa: E731
    text = lambda x: isinstance(x, str) and bool(x)  # noqa: E731
    if set(new) == set(NO_HANDS):
        if live:
            raise Reject("noHands: a run is active")
        if not (zoned(new["startedAt"]) and text(new["itemId"])):
            raise Reject("noHands needs a startedAt with a time zone and a non-empty itemId")
        if new["started"] != [] or any(new[k] is not None for k in ("drain", "endedAt", "endReason")):
            raise Reject("noHands: a new run starts with started [] and drain, endedAt and endReason null")
        ended = cur.get("endedAt")
        if cur.get("itemId") == new["itemId"] or (ended and not (zoned(ended) and parse(new["startedAt"]) > parse(ended))):
            raise Reject("noHands: a new run needs a new itemId and a startedAt later than the last run's endedAt")
        s["noHands"] = new
    elif set(new) == {"drain"}:
        if not (live and not cur.get("drain") and text(new["drain"])):
            raise Reject("noHands: drain is set once, to a string, on an active run")
        cur["drain"] = new["drain"]
    elif set(new) == {"endedAt", "endReason"}:
        if not (live and zoned(new["endedAt"]) and text(new["endReason"])):
            raise Reject("noHands: an active run ends with an endedAt (with a time zone) and an endReason")
        cur.update(new)
    else:
        raise Reject("noHands: set a whole new record, drain, or endedAt with endReason")


def op_pm(s, op):
    need(op, "set")
    keys_ok(op["set"], PM, "pm")
    s.setdefault("pm", {}).update(op["set"])


def dicts(v):
    """A list's dict entries; [] when v is not a list (a hand-edited bad shape)."""
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def op_observe(s, op, notes, filed_now, ticketless):
    """Record a sighting and decide in the same write whether to file a ticket for the kind."""
    need(op, "kind", optional=("ticket",))
    kind, ticket = op["kind"], op.get("ticket")
    if not (kind in KINDS or (isinstance(kind, str) and kind.startswith("other:") and SLUG.fullmatch(kind[6:]))):
        raise Reject(f"unknown observation kind {kind!r}")
    if ticket is not None and not (isinstance(ticket, str) and ID.fullmatch(ticket)):
        raise Reject(f"bad ticket id {ticket!r}")
    if not isinstance(s.get("observed"), dict):
        s["observed"] = {}
    seen = s["observed"]["sightings"] = dicts(s["observed"].get("sightings"))
    filed = s["observed"]["filed"] = dicts(s["observed"].get("filed"))
    if ticket is None:
        new = kind not in ticketless  # one ticketless sighting per kind per apply call
        ticketless.add(kind)
    else:
        new = not any(x.get("kind") == kind and x.get("ticket") == ticket and within(x.get("at"), WEEK) for x in seen)
    if new:
        seen.append({"kind": kind, "ticket": ticket, "at": now()})
    hits = [x for x in seen if x.get("kind") == kind and within(x.get("at"), WEEK)]
    need_n = 1 if kind.startswith("other:") else 2
    last = max((f["at"] for f in filed if f.get("kind") == kind and within(f.get("at"), WEEK)), default=None)
    if len(hits) < need_n:
        why = f"{len(hits)} of {need_n} sightings"
    elif last:
        why = f"filed {last[:10]}"
    elif sum(within(f.get("at"), DAY) for f in filed) >= 3:
        why = "3 filed today"
    elif filed_now[0]:
        why = "one per turn"
    else:
        filed.append({"kind": kind, "at": now()})
        filed_now[0] = True
        counted = ", ".join(f"{x.get('ticket') or '-'} {t(x['at'])}" for x in hits)
        notes.append(f"observe {kind}: file ({counted})")
        return
    notes.append(f"observe {kind}: hold ({why})")


def op_prune(s, op, notes=None):
    need(op)
    for k in [k for k in s if k not in TOP]:
        del s[k]
        if notes is not None:
            notes.append(f"dropped unknown key {k}")
    for tid, m in list(s["merged"].items()):
        if not isinstance(m, dict):
            m = s["merged"][tid] = {"pr": m, "at": now()}
        elif older_than_day(m.get("at")):
            del s["merged"][tid]
    if isinstance(s.get("observed"), dict):
        for k in ("sightings", "filed"):
            s["observed"][k] = [x for x in dicts(s["observed"].get(k)) if within(x.get("at"), WEEK)]


OPS = {
    "start": op_start, "stage": op_stage, "set": op_set, "merged": op_merged, "drop": op_drop,
    "top": op_top, "pm": op_pm,
    "prune": op_prune, "observe": op_observe, "no-hands": op_no_hands,
}


def apply_ops(state, ops):
    """Return (new state, change lines, notes). Raises Reject("op <i>: <reason>")."""
    s = copy.deepcopy(state)
    for k, empty in (("tickets", {}), ("merged", {})):
        s.setdefault(k, empty)
    notes, filed_now, ticketless = [], [False], set()  # filed_now: an observe op already said file in this call
    if not isinstance(ops, list):
        raise Reject("op 0: expected a JSON list of operations")
    for i, op in enumerate(ops):
        try:
            if not isinstance(op, dict) or op.get("op") not in OPS:
                raise Reject(f"unknown op {op.get('op') if isinstance(op, dict) else op!r}")
            if op["op"] == "prune":
                op_prune(s, op, notes)
            elif op["op"] == "observe":
                op_observe(s, op, notes, filed_now, ticketless)
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
    tickets = state.get("tickets")
    for x in tickets.values() if isinstance(tickets, dict) else ():
        if isinstance(x, dict) and x.get("stage") == "awaiting-spec":  # the pre-CW-177 name
            x["stage"] = "awaiting-build"
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
    try:  # the ticket left Todo or Backlog; a failure here never changes the result
        ids = [o["ticket"] for o in ops if isinstance(o, dict) and o.get("op") in ("start", "merged", "drop")]
        if ids:
            cos_lists.remove(ids, path.with_name("tracker-lists.json"))
    except Exception:
        pass
    return 0


# ---- show ----------------------------------------------------------------------------


def t(s):
    """H:MMam/pm for a time on today's UTC date (no space: show prints key=value pairs), the full string otherwise, - for none."""
    if not s:
        return "-"
    d = parse(s)
    return clock12(d.astimezone(timezone.utc)).replace(" ", "") if d and d.date() == datetime.now(timezone.utc).date() else s


def v(x):
    return "-" if x in (None, "") else json.dumps(x, separators=(",", ":")) if isinstance(x, (dict, bool)) else x


def takeover_text(x):
    return f"{x.get('mode')} since {t(x.get('startedAt'))}" if isinstance(x, dict) else "-"


def show(s):
    tk = s.get("tickets", {})
    by = lambda *stages: [(i, x) for i, x in tk.items() if x.get("stage") in stages]  # noqa: E731
    out = [
        f"chief={v(s.get('chiefThreadId'))} paused={v(s.get('paused'))} "
        f"rateLimitedAt={t(s.get('rateLimitedAt'))} wakeTaskId={v(s.get('wakeTaskId'))} "
        f"wakeAt={t(s.get('wakeAt'))} reset={v(s.get('reset'))} takeover={takeover_text(s.get('takeover'))} "
        f"lastResetAt={t(s.get('lastResetAt'))} lastRelayAt={t(s.get('lastRelayAt'))} skillCommit={(s.get('skillCommit') or '-')[:7]} "
        f"chiefSessionId={v(s.get('chiefSessionId'))} takeoverContext={v(s.get('takeoverContext'))}",
        "counts " + " ".join(f"{n}={len(by(n))}" for n in ACTIVE)
        + f" active={len(by(*ACTIVE))} awaiting-build={len(by('awaiting-build'))}"
        f" awaiting-review={len(by('awaiting-review'))} awaiting-merge={len(by('awaiting-merge'))} blocked={len(by('blocked'))}",
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
    pm = s.get("pm") if isinstance(s.get("pm"), dict) else {}
    ranked = " ".join(
        f"{r.get('id')}({r.get('readiness')})" for r in pm.get("ranked") or [] if isinstance(r, dict)
    )
    out += [
        "merged (24h): " + (", ".join(recent) or "-"),
        f"pm: rankedAt={t(pm.get('rankedAt'))} lastDailyAt={t(pm.get('lastDailyAt'))} "
        f"lastCheckAt={t(pm.get('lastCheckAt'))} ranked={ranked or '-'}",
        "unknown keys: " + (" ".join(k for k in s if k not in TOP) or "-"),
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
    sub.add_parser("now").add_argument("--iso", action="store_true")
    sub.add_parser("title").add_argument("ticket")
    cp = sub.add_parser("comment")
    cp.add_argument("kind", choices=("approved", "auto", "withdrawn"))
    cp.add_argument("what", nargs="?")
    cp.add_argument("--head")
    cp.add_argument("--queued")
    cp.add_argument("--tolerance")
    a = ap.parse_args(argv)

    if a.cmd == "now":
        print(now() if a.iso else stamp_text(now()))
        return 0

    if a.cmd == "title":
        if not ID.match(a.ticket):
            print(f"cos_state: title: {a.ticket!r} is not a ticket id", file=sys.stderr)
            return 2
        print(display_title(a.ticket, sys.stdin.read()))
        return 0

    if a.cmd == "comment":
        try:
            print(approval_comment(a.kind, a.what, sys.stdin.read().strip(), a.head, a.queued, a.tolerance, stamp_text(now())))
        except Reject as e:
            print(f"cos_state: comment: {e}", file=sys.stderr)
            return 2
        return 0

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
