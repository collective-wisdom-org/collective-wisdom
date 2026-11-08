#!/usr/bin/env python3
"""The head check for a merge approval: did the PR head move, or does the PR now conflict?

Usage:
    ~/.collective-wisdom/scripts/cos_head_check.py <PREFIX>-N [--file STATE] [--no-approval] [--prs FILE]

Read only: writes, comments and sends nothing. Reads the ticket's `pr` and `headSha` from .agent-team/state.json
(under the repo root unless --file is given), `~/.collective-wisdom/scripts/gh.sh pr view <pr> --json
headRefOid,mergeable` (--prs FILE reads {"<N>": <that JSON>} instead; tests do) and, only when the PR conflicts,
`Review after conflict resolution` from project.md on origin/<target> (project_config.review_after_conflict()).
Prints the relay to send (none for `ok`), then a last line, exit 0:
    head-check: ok                         (head unchanged, not conflicting)
    head-check: moved <old> <new>          (short SHAs; withdraw the approval, send the relay to the build lane)
    head-check: conflict keep              (head unchanged, conflicting, setting off: keep the approval, send the
                                           relay, which carries it, to the merge lane)
    head-check: conflict withdraw          (setting on, or --no-approval: send the relay, which carries none, to the
                                           build lane)
A failed read of `Review after conflict resolution` counts as `on` (`conflict withdraw`). Exit 2 prints "head-check: cannot <what>" when
the state is unreadable, a gh read fails, or the merge target branch is missing or unusable.
--no-approval is for a ticket with no approval to carry (`approve N` on `awaiting-review`): a conflict is then
always `conflict withdraw`.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402

ROOT = root()
GH = str(Path(__file__).absolute().parent / "gh.sh")
FULL_SHA = re.compile(r"[0-9a-f]{40}")
TICKET = project_config.ticket_re()
MOVED = (
    "CHIEF OF STAFF: the PR head moved from {old} to {new} after the user approved. Re-check the reviews per "
    "ship-loop § Phases, 4. Security review (run ~/.collective-wisdom/scripts/review_gate.py) and report MERGE READY again."
)
CONFLICT = "CHIEF OF STAFF: the PR conflicts with {target}. Resolve it per open-pr § Conflict resolution and report MERGE READY."
CONFLICT_APPROVED = (
    "CHIEF OF STAFF: the PR conflicts with {target}. The user approved the merge at head {head}. "
    "Resolve it per open-pr § Conflict resolution and merge."
)


class Cannot(Exception):
    """The check could not run. The message is a fixed phrase, never text from GitHub."""


def read_pr(n, prs):
    try:
        if prs is not None:
            raw = prs[str(n)]
        else:
            p = subprocess.run([GH, "pr", "view", str(n), "--json", "headRefOid,mergeable"],
                               cwd=ROOT, capture_output=True, text=True, timeout=30)
            if p.returncode:
                raise Cannot("read the PR")
            raw = json.loads(p.stdout)
        head, mergeable = raw["headRefOid"], raw["mergeable"]
    except Cannot:
        raise
    except (KeyError, TypeError, ValueError, OSError, subprocess.TimeoutExpired):
        raise Cannot("read the PR")
    if not (isinstance(head, str) and FULL_SHA.fullmatch(head) and isinstance(mergeable, str)):
        raise Cannot("read the PR")
    return head, mergeable


def read_ticket(path, tid):
    try:
        info = json.loads(Path(path).read_text())["tickets"][tid]
        pr, head = info["pr"], info["headSha"]
        pr = int(pr) if isinstance(pr, str) and re.fullmatch(r"[0-9]+", pr) else pr
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        raise Cannot("read the ticket in state")
    if not (type(pr) is int and isinstance(head, str) and FULL_SHA.fullmatch(head)):
        raise Cannot("read pr and headSha in state")
    return pr, head


def check(pr, stored, live, mergeable, no_approval, setting):
    """(relay or None, last line). setting is a function returning `off` or `on`, called only on a conflict."""
    if live != stored:
        return MOVED.format(old=stored[:7], new=live[:7]), f"head-check: moved {stored[:7]} {live[:7]}"
    if mergeable != "CONFLICTING":
        return None, "head-check: ok"
    try:
        target, rule = project_config.target_branch(), setting()
    except SystemExit:
        raise Cannot("read the merge target branch")
    if rule == "off" and not no_approval:
        return CONFLICT_APPROVED.format(target=target, head=live[:7]), "head-check: conflict keep"
    return CONFLICT.format(target=target), "head-check: conflict withdraw"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Head check for a merge approval.")
    ap.add_argument("ticket")
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--no-approval", action="store_true")
    ap.add_argument("--prs", type=Path)
    args = ap.parse_args(argv)
    try:
        if not TICKET.fullmatch(args.ticket):
            raise Cannot("use a ticket id like <PREFIX>-N")
        pr, stored = read_ticket(args.file, args.ticket)
        prs = None
        if args.prs:
            try:
                prs = json.loads(args.prs.read_text())
            except (OSError, UnicodeDecodeError, ValueError):
                raise Cannot("read the PR file")
        live, mergeable = read_pr(pr, prs)
        relay, last = check(pr, stored, live, mergeable, args.no_approval, project_config.review_after_conflict)
    except Cannot as e:
        print(f"head-check: cannot {e}")
        return 2
    if relay:
        print(relay)
    print(last)
    return 0


if __name__ == "__main__":
    sys.exit(main())
