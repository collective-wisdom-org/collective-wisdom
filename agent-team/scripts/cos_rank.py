#!/usr/bin/env python3
"""Check the Backlog ranking child's list and save it as pm.ranked, or say whether a dry pick needs a new ranking.

Usage:
    ~/.collective-wisdom/scripts/cos_rank.py [--file PATH] --started <ISO Z> [--backlog-count N] [--post] < child_message
    ~/.collective-wisdom/scripts/cos_rank.py dry [--file PATH] [--out-of-date]

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

dry is the project-manager skill's Dry ranking test. It reads pm.rankedAt, pm.rankedReady, pm.ranked and merged
from state, writes nothing, and prints one line: "dry: rank (<reason>)" or "dry: check backlog since <pm.rankedAt>".
It checks in order: pm.rankedAt null or not YYYY-MM-DDTHH:MM:SSZ (never ranked); pm.rankedReady (ready tickets used
up); --out-of-date (the pick found a ranked ticket moved, labelled agent-skip, blocked or held); a merged entry whose
`at` is after pm.rankedAt (a bare number counts as merged now); a held entry in pm.ranked and one
`~/.collective-wisdom/scripts/gh.sh pr list --state closed --limit 1 --search "closed:>=<pm.rankedAt>" --json number`
that returns a PR (a failed read counts as none). Otherwise the agent makes one Backlog list-tickets since that time:
a ticket back means rank, none means the Backlog is dry. Exit 2 and "cos_rank: <reason>" when state cannot be read.
"""

import argparse
import contextlib
import io
import json
import re
import subprocess
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


def closed_prs_since(ranked_at):
    """True when a PR closed at or after ranked_at (one GET read). A failed read is False."""
    cmd = [
        str(Path(__file__).absolute().parent / "gh.sh"), "pr", "list", "--state", "closed", "--limit", "1",
        "--search", f"closed:>={ranked_at}", "--json", "number",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        found = json.loads(p.stdout) if p.returncode == 0 else []
    except (subprocess.SubprocessError, OSError, ValueError):
        return False
    return isinstance(found, list) and bool(found)


def dry(argv):
    ap = argparse.ArgumentParser(prog="cos_rank.py dry")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--out-of-date", action="store_true")
    a = ap.parse_args(argv)
    state = cos_state.load(a.file)
    pm = state.get("pm") if isinstance(state.get("pm"), dict) else {}
    at = pm.get("rankedAt")
    since = cos_state.parse(at) if isinstance(at, str) and STARTED.match(at) else None
    if since is None:
        return "dry: rank (never ranked)"
    if pm.get("rankedReady") is True:
        return "dry: rank (the ready tickets are used up)"
    if a.out_of_date:
        return "dry: rank (a ranked ticket is out of date)"
    merged = state.get("merged") if isinstance(state.get("merged"), dict) else {}
    for m in merged.values():
        when = cos_state.parse(m.get("at")) if isinstance(m, dict) else None
        if not isinstance(m, dict) or when is None or when > since:  # a bare number is a PR merged now
            return "dry: rank (a PR merged since the last ranking)"
    ranked = pm.get("ranked") if isinstance(pm.get("ranked"), list) else []
    held = any(isinstance(e, dict) and str(e.get("readiness")).startswith("held: ") for e in ranked)
    if held and closed_prs_since(at):
        return "dry: rank (a PR closed since the last ranking)"
    return f"dry: check backlog since {at}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["dry"]:
        print(dry(argv[1:]))
        return 0
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
