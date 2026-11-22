#!/usr/bin/env python3
"""The Chief of Staff's `status` tables, built from state.

Usage:
    ~/.collective-wisdom/scripts/cos_status.py [--file STATE] [--db PATH] [--ticket <PREFIX>-N] [--sweep "<the sweep's last line>"]

Reads .agent-team/state.json (under the repo root unless --file is given) through cos_state.load and writes nothing. Prints the layout of
chief-of-staff/status.md § Status layout: one markdown table per group, under a bold header with the row count, empty groups left out:

    **Awaiting merge approval (1)**

    | Ticket | Risk | Next |
    |---|---|---|
    | **ABC-197** CSV export<br>[ABC-197](t3-thread://v2/<environment id>/<child thread id>) | High (touches auth) | <detail> $14.20 so far |

Groups, in this order, by stage: Awaiting merge approval (awaiting-merge), Awaiting teammate review (awaiting-review), Merging (merge),
Queued to merge (merge-queued), Speccing (spec), Awaiting build approval (awaiting-build), Building (build), Queued to build (build-queued),
Waiting to spec (spec-queued), Other (blocked). The queued groups list tickets in `queuedAt` order, the order they start (the `queue <lane>:`
lines of `cos_state.py show`); the other groups keep state order.

Each cell comes from state, so the model has only the detail cell to shorten, and the findings of this turn's reads to add:
    Ticket   `**<ID>** <short title>`, then `<br>[<ID>](<thread link>)` for the ticket's childThreadId. The title is `title` in state, cut by
             cos_state.display_title (six words, marker words leave the ID alone); with none, the ID alone (the model fills it from one
             `list-tickets` call). The link is T3's `t3-thread://v2/<environment id>/<thread id>` (the environment id file next to --db);
             a row with no childThreadId, or with no readable environment id, has no `<br>` and no link.
    Risk     the `Risk: <Level> (<reason>).` tail of the ticket's `status` line (Low, Medium or High) as `<Level> (<reason>)`, or `not rated yet`
             when the line has no such tail. Only a tail at the very end counts.
    Next     the `status` line without the Risk tail, copied as written (the model shortens it to what changed or what the user must do, and
             adds the reply, `approve N`, for a ticket waiting on the user), then ` $X so far`. X is the `cost $X` of `agent_usage.py --ticket`
             for the ticket (agent_usage.ticket_line, in process); ` cost unknown` when that line says `cost unknown` or the call fails;
             nothing when no session ran the ticket. A `|` in a cell is written `\\|` and line breaks become spaces.

--ticket <PREFIX>-N prints only that ticket's group and row (the `where's` answer). A ticket that is not in state prints
`<PREFIX>-N, merged (#PR)` when the merged list has it and exits 0; otherwise `cos_status: <PREFIX>-N is not in state` on stdout and exit 1.
--sweep is the last line of this turn's `cos_sweep.py` (`sweep: read in full: ...; merged: ABC-2 #14; untracked: ABC-5 #12, ABC-6`). Its `merged:`
and `untracked:` parts, when they list tickets, add one line each after the tables, with the IDs and PR numbers only (the model adds titles and
the tracker state):
    Merged: ABC-2 (#14); ABC-3 (#15)
    Not in my state: ABC-5 (#12); ABC-6
Not printed here, for the model: the `Filling stopped:` line (the tick's `report` line gives it), the full block for each pending approval,
the No Hands line, and the `Awaiting teammate review` names from the sweep's `waiting` line.
Exit 0 with the tables (nothing at all for an empty state), 1 for a `--ticket` not in state, 2 with `cos_status: <what>` for an unreadable state
file or a bad argument.
"""

import argparse
import io
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402

GROUPS = [  # (header, stage)
    ("Awaiting merge approval", "awaiting-merge"),
    ("Awaiting teammate review", "awaiting-review"),
    ("Merging", "merge"),
    ("Queued to merge", "merge-queued"),
    ("Speccing", "spec"),
    ("Awaiting build approval", "awaiting-build"),
    ("Building", "build"),
    ("Queued to build", "build-queued"),
    ("Waiting to spec", "spec-queued"),
    ("Other", "blocked"),
]
RISK = re.compile(r"\s*Risk: (?P<level>Low|Medium|High) \((?P<why>.*)\)\.?\s*$")
NOT_RATED = "not rated yet"
THREAD = re.compile(r"[A-Za-z0-9._:%@][A-Za-z0-9._:%@-]*")


class Cannot(Exception):
    pass


def cell(text):
    """Table cell text: line breaks become spaces and `|` is escaped."""
    return " ".join(str(text).split()).replace("|", "\\|")


def split_risk(status):
    """(status without its Risk tail, `<Level> (<reason>)` or `not rated yet`)."""
    status = status if isinstance(status, str) else ""
    m = RISK.search(status)
    if not m:
        return status.strip(), NOT_RATED
    return status[: m.start()].strip(), f"{m['level']} ({m['why']})"


def cost_of(tid):
    """` $X so far`, ` cost unknown` or "" (no session ran the ticket), from agent_usage.ticket_line. Never raises."""
    try:
        import agent_usage

        line = agent_usage.ticket_line(Path.home() / ".claude" / "projects", tid, None, Path.home() / ".cursor" / "projects")
    except (Exception, SystemExit):
        return " cost unknown"
    if line is None:
        return ""
    m = re.match(r"cost \$([0-9]+(?:\.[0-9]+)?)", line)
    return f" ${m[1]} so far" if m else " cost unknown"


def thread_link(db, thread):
    """`[...]` target `t3-thread://v2/<environment id>/<thread id>`, or None."""
    if not (isinstance(thread, str) and THREAD.fullmatch(thread)):
        return None
    try:
        import cos_idle_check

        env = cos_idle_check.environment_id(db or cos_idle_check.DEFAULT_DB)
    except (Exception, SystemExit):
        return None
    return f"t3-thread://v2/{env}/{thread}" if env else None


def ticket_cell(tid, t, db):
    title = cos_state.display_title(tid, t.get("title") if isinstance(t.get("title"), str) else "")
    out = f"**{tid}**" + (f" {cell(title.removeprefix(tid + ': '))}" if title != tid else "")
    link = thread_link(db, t.get("childThreadId"))
    return out + (f"<br>[{tid}]({link})" if link else "")


def row(tid, t, db):
    detail, risk = split_risk(t.get("status"))
    return f"| {ticket_cell(tid, t, db)} | {cell(risk)} | {cell(detail + cost_of(tid))} |"


def table(header, rows):
    return [f"**{header} ({len(rows)})**", "", "| Ticket | Risk | Next |", "|---|---|---|", *rows, ""]


def ordered(tickets, stage):
    found = [(i, t) for i, t in tickets.items() if isinstance(t, dict) and t.get("stage") == stage]
    return sorted(found, key=lambda p: p[1].get("queuedAt") or "") if stage.endswith("-queued") else found


def sweep_lines(sweep):
    """`Merged: ...` and `Not in my state: ...` from the sweep's last line (only well-formed `<ID> #N` and `<ID>` items)."""
    out = []
    for key, label in (("merged", "Merged"), ("untracked", "Not in my state")):
        m = re.search(rf"(?:^|; ){key}: ([^;]*)", sweep or "")
        items = []
        for x in (m.group(1).split(", ") if m else []):
            words = x.split()
            if words and cos_state.ID.fullmatch(words[0]) and (len(words) == 1 or len(words) == 2 and re.fullmatch(r"#\d+", words[1])):
                items.append(f"{words[0]} ({words[1]})" if len(words) == 2 else words[0])
        if items:
            out.append(f"{label}: " + "; ".join(items))
    return out


def build(state, db=None, only=None, sweep=None):
    tickets = state.get("tickets") if isinstance(state.get("tickets"), dict) else {}
    if only and only not in tickets:
        merged = (state.get("merged") or {}).get(only)
        if isinstance(merged, dict) and isinstance(merged.get("pr"), int):
            return [f"{only}, merged (#{merged['pr']})"], 0
        return [f"cos_status: {only} is not in state"], 1
    out = []
    for header, stage in GROUPS:
        rows = [row(i, t, db) for i, t in ordered(tickets, stage) if not only or i == only]
        if rows:
            out += table(header, rows)
    return [*out, *sweep_lines(sweep)] if not only else out, 0


def load(path):
    try:
        with redirect_stderr(io.StringIO()):
            state = cos_state.load(path)
    except SystemExit:
        raise Cannot("unreadable state file")
    if not isinstance(state, dict):
        raise Cannot("unreadable state file")
    return state


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"cos_status: {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="The Chief of Staff's status tables, from state.")
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("--db", type=Path)
    ap.add_argument("--ticket")
    ap.add_argument("--sweep")
    args = ap.parse_args(argv)
    try:
        if args.ticket and not cos_state.ID.fullmatch(args.ticket):
            raise Cannot("--ticket needs an id like <PREFIX>-N")
        lines, code = build(load(args.file), args.db, args.ticket, args.sweep)
    except Cannot as e:
        print(f"cos_status: {e}")
        return 2
    if lines:
        print("\n".join(lines).rstrip("\n"))
    return code


if __name__ == "__main__":
    sys.exit(main())
