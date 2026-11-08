#!/usr/bin/env python3
"""The project manager's hygiene rules, as one line per ticket to act on.

Usage:
    ~/.collective-wisdom/scripts/pm_hygiene.py fill  [--file STATE] < list-tickets JSON
    ~/.collective-wisdom/scripts/pm_hygiene.py drift [--file STATE] --since <pm.lastCheckAt> < {"prs": [...], "tickets": {...}}
    ~/.collective-wisdom/scripts/pm_hygiene.py stale [--file STATE] < list-tickets JSON

--file defaults to .agent-team/state.json under the repo root. Reads `tickets`, `merged` and `pm` from it and JSON from
stdin (the calls the hygiene child already makes). Writes nothing: no state, no tracker. Exit 2 and "pm_hygiene: <what>"
when state or stdin cannot be read. Tickets in the Chief of Staff's `tickets` are never listed.

fill: stdin is the change check's list-tickets result as the tracker adapter returns it (a JSON list). Linear shape:
id, state, labels, priority. GitHub shape: number (id is ABC-<number>), labels, and state, stateReason when present;
the state is the furthest-along `status:` label (none is Backlog; closed is Done, or Canceled when not planned) and
the priority is the `priority:` label. For each ticket
in Backlog, Todo, In Progress or In Review, prints
    ABC-N fill: priority, area, type
for the fields that are empty and not in pm.filled[ABC-N]. `area` is listed only when project.md's Areas and labels
section names area labels (`none` means no areas). An area label is one of those; a type label is Bug, Feature or
Improvement (or type:bug, type:feature, type:improvement).

drift: --since is pm.lastCheckAt. "prs" is the change check's PR list (number, state, headRefName, title, createdAt,
mergedAt). A PR belongs to ticket ABC-N when abc-N is in its branch or (ABC-N) is in its title. With "tickets" empty
it prints "get ABC-N #PR" for each PR that could move its ticket: merged after --since, or opened after it and still
open. The child then reads those tickets (state, labels) and runs it again with "tickets" filled ({"ABC-N": {"state":
..., "labels": [...]}}, in the adapter's shape as for fill; GitHub also stateReason); it prints
    move ABC-N Done (PR #X merged)         merged after --since, ticket not Done, Canceled or Duplicate
    move ABC-N In Review (PR #X open)      opened after --since, still open, ticket in Backlog, Todo or In Progress
A ticket labelled `agent` is skipped unless it is in `merged` in state, and then only the move to Done applies.

stale: stdin is the In Progress and In Review lists (id, title, state, updatedAt; one JSON list per call, or both
concatenated). For each ticket whose updatedAt is over 3 days old, it reads the ticket's PRs
(`gh.sh pr list --state all --search "ABC-N" --json number,updatedAt,headRefName`) and the last commit of each PR branch
(`gh.sh api -X GET repos/<owner>/<repo>/commits -f sha=<branch> -f per_page=1`, only for a branch matching
^[A-Za-z0-9._/-]+$). The newest of the three times is the last activity; when that is over 3 days old and its date
differs from pm.flaggedStale[ABC-N], it prints
    stale ABC-N In Progress since 2026-11-01
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import project_config  # noqa: E402

ACTIVE = ("Backlog", "Todo", "In Progress", "In Review")
FINISHED = ("Done", "Canceled", "Cancelled", "Duplicate")
TYPES = {"bug", "feature", "improvement", "type:bug", "type:feature", "type:improvement"}
STALE_AFTER = timedelta(days=3)
BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


class Bad(Exception):
    pass


def now():
    return datetime.now(timezone.utc)


def gh(args):
    """stdout of one `gh.sh` read (GET only); raises OSError when it fails."""
    cmd = [str(Path(__file__).absolute().parent / "gh.sh"), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.SubprocessError as e:
        raise OSError(type(e).__name__)
    if p.returncode:
        raise OSError(f"exit {p.returncode}")
    return p.stdout


def read_json_values(text):
    """Every JSON value in text, in order (the child may paste two list-tickets results back to back)."""
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return out
        try:
            v, i = dec.raw_decode(text, i)
        except ValueError:
            raise Bad("stdin is not JSON") from None
        out.append(v)


def ticket_list(text):
    """The ticket objects from stdin: lists, or objects holding an `issues` or `tickets` list."""
    found = []
    for v in read_json_values(text):
        if isinstance(v, dict):
            v = v.get("issues") if isinstance(v.get("issues"), list) else v.get("tickets")
        if not isinstance(v, list):
            raise Bad("stdin is not a ticket list")
        for t in v:
            tid = ticket_id(t) if isinstance(t, dict) else None
            if tid:
                found.append({**t, "id": tid})
    return found


def ticket_id(t):
    """`ABC-N` from the Linear shape's `id`, or from a GitHub issue's `number`; None when neither fits."""
    tid = t.get("id")
    if tid is None and type(t.get("number")) is int:
        tid = f"{project_config.prefix()}-{t['number']}"
    return tid if isinstance(tid, str) and cos_state.ID.match(tid) else None


def name_of(x):
    """A state or label as text: a string, or an object with a `name`."""
    if isinstance(x, dict):
        x = x.get("name")
    return x if isinstance(x, str) else ""


def labels_of(t):
    labels = t.get("labels")
    if isinstance(labels, dict):  # {"nodes": [...]}
        labels = labels.get("nodes")
    return {name_of(x).lower() for x in labels} if isinstance(labels, list) else set()


STATUS_LABELS = (("status:in-review", "In Review"), ("status:in-progress", "In Progress"), ("status:todo", "Todo"))


def state_of(t):
    """The ticket's state name. A named state (Linear) is used as is. A GitHub issue (`state` OPEN or CLOSED, or no
    `state`) reads from its labels and stateReason: the furthest-along `status:` label, Backlog when it has none,
    Done when closed as completed, Canceled when closed as not planned."""
    named = name_of(t.get("state"))
    if named and named.upper() not in ("OPEN", "CLOSED"):
        return named
    if named.upper() == "CLOSED":
        return "Canceled" if str(t.get("stateReason", "")).upper() == "NOT_PLANNED" else "Done"
    have = labels_of(t)
    return next((name for label, name in STATUS_LABELS if label in have), "Backlog")


def when(s):
    t = cos_state.parse(s)
    return t if t is not None and t.tzinfo else None


def area_labels():
    """Lower-case area label names from project.md's Areas and labels section; empty when `none` or unset."""
    try:
        text = Path(os.environ.get("PROJECT_MD") or project_config.DEFAULT).read_text()
    except OSError:
        return set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip().lower() == "areas and labels"
        m = in_section and re.match(r"\s*[-*]\s*Area labels:\s*(.*)", line, re.I)
        if m:
            return {t.lower() for t in re.findall(r"`([^`]+)`", re.split(r"Type labels", m.group(1), flags=re.I)[0])}
    return set()


def priority_empty(t):
    if any(l in labels_of(t) for l in ("priority:urgent", "priority:high", "priority:medium", "priority:low")):
        return False
    p = t.get("priority")
    if isinstance(p, dict):
        p = p.get("name") if p.get("name") is not None else p.get("value")
    return p in (None, "", 0, "0") or (isinstance(p, str) and p.lower() == "no priority")


def fill(state, text):
    filled = state.get("pm", {}).get("filled") if isinstance(state.get("pm"), dict) else None
    filled = filled if isinstance(filled, dict) else {}
    areas = area_labels()
    out = []
    for t in ticket_list(text):
        if t["id"] in state["tickets"] or state_of(t) not in ACTIVE:
            continue
        have = labels_of(t)
        empty = [f for f, is_empty in (
            ("priority", priority_empty(t)),
            ("area", bool(areas) and not (have & areas)),
            ("type", not (have & TYPES)),
        ) if is_empty]
        done = filled.get(t["id"]) if isinstance(filled.get(t["id"]), list) else []
        empty = [f for f in empty if f not in done]
        if empty:
            out.append(f"{t['id']} fill: {', '.join(empty)}")
    return out


def ticket_of(pr):
    """The ticket id a PR belongs to (abc-N in its branch, or (ABC-N) in its title), or None."""
    prefix = project_config.prefix()
    branch = pr.get("headRefName")
    m = isinstance(branch, str) and re.search(rf"(?<![a-z0-9]){re.escape(prefix.lower())}-(\d+)(?!\d)", branch.lower())
    if not m:
        title = pr.get("title")
        m = isinstance(title, str) and re.search(rf"\(({re.escape(prefix)}-\d+)\)", title)
        return m.group(1) if m else None
    return f"{prefix}-{int(m.group(1))}"


def drift(state, text, since):
    try:
        data = json.loads(text)
    except ValueError:
        raise Bad("stdin is not JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("prs"), list) or not isinstance(data.get("tickets", {}), dict):
        raise Bad('stdin needs {"prs": [...], "tickets": {...}}')
    tickets = data.get("tickets", {})
    merged_prs, open_prs = {}, {}  # ticket -> first PR number
    for pr in data["prs"]:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            continue
        tid = ticket_of(pr)
        if tid is None or tid in state["tickets"]:
            continue
        status = str(pr.get("state", "")).upper()
        merged_at, created_at = when(pr.get("mergedAt")), when(pr.get("createdAt"))
        if merged_at and merged_at > since:
            merged_prs.setdefault(tid, []).append(pr["number"])
        elif status == "OPEN" and created_at and created_at > since:
            open_prs.setdefault(tid, []).append(pr["number"])
    if not tickets:
        return [f"get {tid} #{n}" for group in (merged_prs, open_prs) for tid, nums in group.items() for n in nums]
    out = []
    for tid in dict.fromkeys([*merged_prs, *open_prs]):
        t = tickets.get(tid)
        if not isinstance(t, dict):
            continue
        status = state_of(t)
        agent_merged = "agent" in labels_of(t) and tid in state.get("merged", {})
        if "agent" in labels_of(t) and not agent_merged:
            continue
        if tid in merged_prs and status not in FINISHED:
            out.append(f"move {tid} Done (PR #{merged_prs[tid][0]} merged)")
        elif tid in open_prs and not agent_merged and tid not in merged_prs and status in ("Backlog", "Todo", "In Progress"):
            out.append(f"move {tid} In Review (PR #{open_prs[tid][0]} open)")
    return out


def stale(state, text):
    pm = state.get("pm") if isinstance(state.get("pm"), dict) else {}
    flagged = pm.get("flaggedStale") if isinstance(pm.get("flaggedStale"), dict) else {}
    repo = project_config.repo()
    cutoff = now() - STALE_AFTER
    out = []
    for t in ticket_list(text):
        updated = when(t.get("updatedAt"))
        if t["id"] in state["tickets"] or updated is None or updated >= cutoff:
            continue
        times = [updated]
        try:
            prs = json.loads(gh(["pr", "list", "--state", "all", "--search", t["id"],
                                 "--json", "number,updatedAt,headRefName"]))
        except (OSError, ValueError):
            out.append(f"pm_hygiene: could not read PRs for {t['id']}, not checked")
            continue
        branches = set()
        for pr in prs if isinstance(prs, list) else []:
            if isinstance(pr, dict):
                times += [x for x in [when(pr.get("updatedAt"))] if x]
                if isinstance(pr.get("headRefName"), str) and BRANCH.match(pr["headRefName"]):
                    branches.add(pr["headRefName"])
        for branch in sorted(branches) if repo else []:
            try:
                commits = json.loads(gh(["api", "-X", "GET", f"repos/{repo}/commits", "-f", f"sha={branch}", "-f", "per_page=1"]))
                c = commits[0]["commit"]
                times += [x for x in [when((c.get("committer") or {}).get("date")), when((c.get("author") or {}).get("date"))] if x]
            except (OSError, ValueError, LookupError, TypeError, AttributeError):
                pass  # a deleted branch has no commit to read
        newest = max(times)
        date = newest.strftime("%Y-%m-%d")
        if newest < cutoff and str(flagged.get(t["id"], ""))[:10] != date:
            out.append(f"stale {t['id']} {state_of(t)} since {date}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fill", "drift", "stale"):
        p = sub.add_parser(name)
        p.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    sub.choices["drift"].add_argument("--since", required=True)
    a = ap.parse_args(argv)
    try:
        state = cos_state.load(a.file)
        if not isinstance(state.get("tickets"), dict):
            raise Bad("unreadable state file")
        if not isinstance(state.get("merged", {}), dict):
            raise Bad("unreadable state file")
        text = sys.stdin.read()
        if a.cmd == "fill":
            lines = fill(state, text)
        elif a.cmd == "stale":
            lines = stale(state, text)
        else:
            since = when(a.since)
            if since is None:
                raise Bad("bad --since")
            lines = drift(state, text, since)
    except Bad as e:
        print(f"pm_hygiene: {e}")
        return 2
    except SystemExit as e:
        if isinstance(e.code, str):  # project_config's "project.md: ..." message
            print("pm_hygiene: bad project.md")
            return 2
        raise
    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
